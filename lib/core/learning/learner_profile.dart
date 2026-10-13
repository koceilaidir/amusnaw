/// Profil de l'apprenant : ce que le prof sait de lui.
/// Stocké côté serveur (VPS) et en cache local pour le hors-ligne.
enum CefrLevel { a1, a2, b1, b2 }

enum LearningGoal { family, songs, culture, travel, roots, other }

class LearnerProfile {
  LearnerProfile({
    required this.name,
    required this.interfaceLanguage,
    this.level = CefrLevel.a1,
    this.goals = const [],
    this.background = '',
    this.knownWords = const {},
    this.frequentErrors = const {},
    this.lastSessionAt,
  });

  final String name;

  /// Langue dans laquelle le prof explique (en, fr, ar, es…).
  final String interfaceLanguage;

  CefrLevel level;

  /// Pourquoi il apprend : le prof y relie chaque leçon (motivation).
  List<LearningGoal> goals;

  /// Ce qu'il raconte de lui (« ma grand-mère parlait kabyle »).
  String background;

  /// Mots déjà rencontrés → ids de MemoryCard.
  Set<String> knownWords;

  /// Erreurs récurrentes et leur fréquence (« accord masc/fém », …).
  Map<String, int> frequentErrors;

  DateTime? lastSessionAt;

  /// Jours depuis la dernière séance : sert à adapter l'accueil
  /// (« on reprend en douceur ») sans jamais culpabiliser.
  int daysAway(DateTime now) =>
      lastSessionAt == null ? 0 : now.difference(lastSessionAt!).inDays;
}
