import 'package:http/http.dart' as http;

/// Téléphone : le client HTTP standard lit déjà la réponse au fil de l'eau.
http.Client streamingClient() => http.Client();
