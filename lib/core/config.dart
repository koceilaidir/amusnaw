/// Valeurs à renseigner avant de tester la connexion.
/// Passe-les au build : flutter run --dart-define=API_BASE_URL=https://api.ton-domaine.com
class AppConfig {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000', // émulateur Android → localhost du PC
  );

  /// Bouton « Test without an account » (bêta). Toujours actif en debug.
  static const testLogin = bool.fromEnvironment('TEST_LOGIN');

  /// ID client OAuth « Web » de Google Cloud (le serveur vérifie ce jeton).
  static const googleServerClientId = String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID');

  /// Nom et version de l'IA, affichés sous la zone de saisie du chat.
  static const aiName = 'amusnaw 1.0';
}
