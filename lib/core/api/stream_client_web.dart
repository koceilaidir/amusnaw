import 'package:fetch_client/fetch_client.dart';
import 'package:http/http.dart' as http;

/// Navigateur : le client par défaut attend la fin de la réponse ; fetch la
/// lit au fil de l'eau, pour afficher le prof mot par mot.
http.Client streamingClient() => FetchClient(mode: RequestMode.cors);
