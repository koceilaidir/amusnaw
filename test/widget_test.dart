import 'package:flutter_test/flutter_test.dart';

import 'package:amusnaw/core/learning/spaced_repetition.dart';

void main() {
  test('un mot bien su revient de plus en plus tard', () {
    final now = DateTime(2026, 1, 1);
    final card = MemoryCard(id: 'aman', kabyle: 'aman', translation: 'water', due: now);
    SpacedRepetition.review(card, 5, now: now);
    expect(card.intervalDays, 1);
    SpacedRepetition.review(card, 5, now: now);
    expect(card.intervalDays, 6);
    SpacedRepetition.review(card, 5, now: now);
    expect(card.intervalDays, greaterThan(6));
  });

  test('un mot oublié revient le lendemain', () {
    final now = DateTime(2026, 1, 1);
    final card = MemoryCard(id: 'aɣrum', kabyle: 'aɣrum', translation: 'bread', due: now);
    SpacedRepetition.review(card, 5, now: now);
    SpacedRepetition.review(card, 5, now: now);
    SpacedRepetition.review(card, 1, now: now);
    expect(card.intervalDays, 1);
    expect(card.repetitions, 0);
  });
}
