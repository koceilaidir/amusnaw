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

  Future<Map<String, dynamic>> get(String path) =>
      _send(() async => http.get(
            Uri.parse('${AppConfig.apiBaseUrl}$path'),
            headers: await _headers(),
          ));

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
