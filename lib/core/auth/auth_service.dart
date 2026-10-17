import 'dart:convert';
import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import '../config.dart';
import '../locale/locale_controller.dart';

class AuthException implements Exception {
  AuthException(this.message);
  final String message;
}

class RefreshException implements Exception {
  RefreshException(this.status);
  final int status;
}

class AuthSession {
  AuthSession({required this.token, required this.userId, this.name});
  final String token;
  final String userId;
  final String? name;
}

/// Connexion rapide : l'app obtient un jeton d'identité chez Google ou
/// Apple, puis l'échange contre un jeton Amusnaw auprès de notre serveur
/// (VPS). Le serveur vérifie la signature du jeton : aucun mot de passe
/// n'est jamais stocké.
class AuthService {
  final _storage = const FlutterSecureStorage();
  final _google = GoogleSignIn(
    scopes: const ['email'],
    serverClientId: AppConfig.googleServerClientId.isEmpty
        ? null
        : AppConfig.googleServerClientId,
  );

  Future<AuthSession?> signInWithGoogle() async {
    final account = await _google.signIn();
    if (account == null) return null; // annulé par l'utilisateur
    final auth = await account.authentication;
    final idToken = auth.idToken;
    if (idToken == null) throw AuthException('Google sign-in failed.');
    return _exchange('/auth/google', {'id_token': idToken});
  }

  Future<AuthSession?> signInWithApple() async {
    try {
      final cred = await SignInWithApple.getAppleIDCredential(
        scopes: [AppleIDAuthorizationScopes.email, AppleIDAuthorizationScopes.fullName],
      );
      final token = cred.identityToken;
      if (token == null) throw AuthException('Apple sign-in failed.');
      // Apple ne donne le nom qu'à la toute première connexion.
      final name = [cred.givenName, cred.familyName]
          .whereType<String>()
          .join(' ')
          .trim();
      return _exchange('/auth/apple', {
        'identity_token': token,
        if (name.isNotEmpty) 'name': name,
      });
    } on SignInWithAppleAuthorizationException catch (e) {
      if (e.code == AuthorizationErrorCode.canceled) return null;
      rethrow;
    }
  }

  Future<AuthSession> _exchange(String path, Map<String, String> body) async {
    final res = await http.post(
      Uri.parse('${AppConfig.apiBaseUrl}$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        ...body,
        'interface_language': localeController.value.code,
      }),
    );
    if (res.statusCode != 200) throw AuthException(_detail(res, 'Connexion impossible (${res.statusCode}).'));
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    final session = AuthSession(
      token: json['access_token'] as String,
      userId: json['user']['id'] as String,
      name: json['user']['name'] as String?,
    );
    await _storage.write(key: 'access_token', value: session.token);
    return session;
  }

  /// Message d'erreur du serveur (« Code incorrect. »…), sinon le message par défaut.
  String _detail(http.Response res, String fallback) {
    try {
      final d = (jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>)['detail'];
      if (d is String && d.isNotEmpty) return d;
    } catch (_) {}
    return fallback;
  }

  /// Ce que le serveur propose à l'accueil : {"email": bool, "guest": bool, "google": bool}.
  Future<Map<String, dynamic>> methods() async {
    try {
      final res = await http
          .get(Uri.parse('${AppConfig.apiBaseUrl}/auth/methods'))
          .timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) return jsonDecode(res.body) as Map<String, dynamic>;
    } catch (_) {}
    return const {};
  }

  /// Connexion par e-mail, étape 1 : le serveur envoie un code à 6 chiffres.
  Future<void> sendEmailCode(String email) async {
    final res = await http.post(
      Uri.parse('${AppConfig.apiBaseUrl}/auth/email/start'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'interface_language': localeController.value.code}),
    ).timeout(const Duration(seconds: 30));
    if (res.statusCode != 200) throw AuthException(_detail(res, 'L’e-mail n’a pas pu être envoyé.'));
  }

  /// Étape 2 : le code reçu. Le compte est créé au premier passage.
  Future<AuthSession> signInWithEmailCode(String email, String code, {String? name}) =>
      _exchange('/auth/email/verify', {
        'email': email,
        'code': code,
        if (name != null && name.isNotEmpty) 'name': name,
      });

  Future<String?> currentToken() => _storage.read(key: 'access_token');

  /// Renouvelle le jeton (appelé à l'ouverture de l'app). Renvoie le profil
  /// serveur, ou lève une exception HTTP (401 = session expirée).
  Future<Map<String, dynamic>> refresh() async {
    final token = await currentToken();
    final res = await http.post(
      Uri.parse('${AppConfig.apiBaseUrl}/auth/refresh'),
      headers: {if (token != null) 'Authorization': 'Bearer $token'},
    ).timeout(const Duration(seconds: 20));
    if (res.statusCode != 200) throw RefreshException(res.statusCode);
    final json = jsonDecode(utf8.decode(res.bodyBytes)) as Map<String, dynamic>;
    await _storage.write(key: 'access_token', value: json['access_token'] as String);
    return json['user'] as Map<String, dynamic>;
  }

  /// Connexion de test (bêta, serveur avec DEV_LOGIN=true) : un compte par
  /// téléphone, sans Google ni Apple.
  Future<AuthSession> signInForTesting({String name = 'Testeur'}) async {
    var deviceId = await _storage.read(key: 'dev_device_id');
    if (deviceId == null) {
      final r = Random.secure();
      deviceId = List.generate(16, (_) => r.nextInt(16).toRadixString(16)).join();
      await _storage.write(key: 'dev_device_id', value: deviceId);
    }
    return _exchange('/auth/dev', {'device_id': deviceId, 'name': name});
  }

  Future<void> signOut() async {
    await _storage.delete(key: 'access_token');
    await _google.signOut();
  }
}

final authService = AuthService();
