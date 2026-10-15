import 'dart:convert';

import 'package:http/http.dart' as http;

import '../auth/auth_service.dart';
import '../config.dart';

class ApiException implements Exception {
  ApiException(this.status, this.message);
  final int status;
  final String message;
  @override
  String toString() => 'ApiException($status): $message';
}

/// Appels authentifiés vers le serveur Amusnaw (VPS).
class ApiClient {
  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) =>
      _send(() async => http.post(
            Uri.parse('${AppConfig.apiBaseUrl}$path'),
            headers: await _headers(),
            body: jsonEncode(body),
          ));

  Future<Map<String, dynamic>> patch(String path, Map<String, dynamic> body) =>
      _send(() async => http.patch(
            Uri.parse('${AppConfig.apiBaseUrl}$path'),
            headers: await _headers(),
            body: jsonEncode(body),
          ));

  Future<Map<String, dynamic>> get(String path) async =>
      (await getAny(path)) as Map<String, dynamic>;

  /// GET dont la réponse peut être une liste ou un objet.
  Future<dynamic> getAny(String path) async {
    final res = await http
        .get(Uri.parse('${AppConfig.apiBaseUrl}$path'), headers: await _headers())
        .timeout(const Duration(seconds: 30));
    final text = utf8.decode(res.bodyBytes);
    if (res.statusCode >= 400) throw ApiException(res.statusCode, text);
    return jsonDecode(text);
  }

  Future<void> delete(String path) async {
    final res = await http
        .delete(Uri.parse('${AppConfig.apiBaseUrl}$path'), headers: await _headers())
        .timeout(const Duration(seconds: 30));
    if (res.statusCode >= 400) throw ApiException(res.statusCode, res.body);
  }

  /// Réponse en continu (Server-Sent Events) : chaque événement `data: {...}`
  /// est renvoyé dès qu'il arrive.
  Stream<Map<String, dynamic>> stream(String path, Map<String, dynamic> body) async* {
    final client = http.Client();
    try {
      final req = http.Request('POST', Uri.parse('${AppConfig.apiBaseUrl}$path'))
        ..headers.addAll(await _headers())
        ..headers['Accept'] = 'text/event-stream'
        ..body = jsonEncode(body);
      final res = await client.send(req).timeout(const Duration(seconds: 30));
      if (res.statusCode >= 400) {
        throw ApiException(res.statusCode, await res.stream.bytesToString());
      }
      final lines = res.stream.transform(utf8.decoder).transform(const LineSplitter());
      await for (final line in lines) {
        if (!line.startsWith('data:')) continue;
        final data = line.substring(5).trim();
        if (data.isEmpty) continue;
        yield jsonDecode(data) as Map<String, dynamic>;
      }
    } finally {
      client.close();
    }
  }

  Future<Map<String, String>> _headers() async {
    final token = await authService.currentToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<Map<String, dynamic>> _send(Future<http.Response> Function() call) async {
    final res = await call().timeout(const Duration(seconds: 90));
    final text = utf8.decode(res.bodyBytes);
    if (res.statusCode >= 400) throw ApiException(res.statusCode, text);
    return jsonDecode(text) as Map<String, dynamic>;
  }
}

final api = ApiClient();
