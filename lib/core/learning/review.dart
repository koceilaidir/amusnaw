import 'dart:math';

import '../../content/sample_content.dart';
import 'spaced_repetition.dart';

/// Transforme les cartes à revoir (SM-2) en questions « que veut dire… ? ».
/// Vide s'il n'y a rien à revoir ou trop peu de mots pour faire des choix.
List<ChoiceExercise> reviewExercises(List<MemoryCard> cards, {int max = 6}) {
  final due = SpacedRepetition.dueToday(cards, max: max);
  final meanings = {for (final c in cards) c.translation}..removeWhere((m) => m.isEmpty);
  if (meanings.length < 3) return const [];
  final rng = Random();
  final out = <ChoiceExercise>[];
  for (final c in due) {
    if (c.translation.isEmpty) continue;
    final others = (meanings.toList()..remove(c.translation)..shuffle(rng)).take(2);
    final options = [c.translation, ...others]..shuffle(rng);
    out.add(ChoiceExercise(
      id: c.id,
      instruction: 'RÉVISION',
      before: c.kabyle,
      options: options,
      answer: c.translation,
      explanation: '${c.kabyle} — ${c.translation}.',
    ));
  }
  return out;
}
