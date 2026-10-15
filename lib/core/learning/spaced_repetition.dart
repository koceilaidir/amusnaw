/// Répétition espacée (Ebbinghaus → Leitner → Pimsleur → SM-2).
///
/// Chaque mot ou tournure appris devient une [MemoryCard]. Après chaque
/// rappel, l'apprenant (ou l'exercice) donne une note de 0 à 5 et on
/// calcule la prochaine date de révision. Un mot bien su revient de plus
/// en plus tard ; un mot oublié revient vite. C'est ce qui permet à
/// l'utilisateur de ne pas venir tous les jours : la séance suivante
/// rattrape d'abord ce qui est « sur le point d'être oublié ».
class MemoryCard {
  MemoryCard({
    required this.id,
    required this.kabyle,
    required this.translation,
    this.repetitions = 0,
    this.intervalDays = 0,
    this.ease = 2.5,
    DateTime? due,
  }) : due = due ?? DateTime.now();

  final String id;
  final String kabyle;
  final String translation;
  int repetitions;
  int intervalDays;
  double ease;
  DateTime due;

  bool isDue(DateTime now) => !due.isAfter(now);

  Map<String, dynamic> toJson() => {
        'id': id,
        'kabyle': kabyle,
        'translation': translation,
        'repetitions': repetitions,
        'intervalDays': intervalDays,
        'ease': ease,
        'due': due.toIso8601String(),
      };

  factory MemoryCard.fromJson(Map<String, dynamic> j) => MemoryCard(
        id: j['id'] as String,
        kabyle: j['kabyle'] as String,
        translation: (j['translation'] as String?) ?? '',
        repetitions: (j['repetitions'] as num?)?.toInt() ?? 0,
        intervalDays: (j['intervalDays'] as num?)?.toInt() ?? 0,
        ease: (j['ease'] as num?)?.toDouble() ?? 2.5,
        due: DateTime.tryParse((j['due'] as String?) ?? ''),
      );
}

class SpacedRepetition {
  /// Algorithme SM-2 (Wozniak). [quality] : 0 = oublié … 5 = parfait.
  static void review(MemoryCard card, int quality, {DateTime? now}) {
    final today = now ?? DateTime.now();
    final q = quality.clamp(0, 5);

    if (q < 3) {
      card.repetitions = 0;
      card.intervalDays = 1;
    } else {
      card.repetitions += 1;
      card.intervalDays = switch (card.repetitions) {
        1 => 1,
        2 => 6,
        _ => (card.intervalDays * card.ease).round(),
      };
    }

    card.ease = (card.ease + 0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        .clamp(1.3, 3.0);
    card.due = today.add(Duration(days: card.intervalDays));
  }

  /// Cartes à revoir en priorité (les plus en retard d'abord),
  /// limitées pour garder une séance courte.
  static List<MemoryCard> dueToday(List<MemoryCard> cards,
      {int max = 8, DateTime? now}) {
    final t = now ?? DateTime.now();
    final due = cards.where((c) => c.isDue(t)).toList()
      ..sort((a, b) => a.due.compareTo(b.due));
    return due.take(max).toList();
  }
}
