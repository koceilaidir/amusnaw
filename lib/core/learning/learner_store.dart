import 'package:flutter/foundation.dart';

import 'spaced_repetition.dart';

/// État local de l'apprenant. Pour l'instant en mémoire ;
/// TODO : persister localement et synchroniser avec le serveur.
class LearnerState {
  const LearnerState({
    this.name = '',
    this.cards = const {},
    this.chats = 0,
    this.capsules = 0,
    this.lastSessionAt,
    this.skills = const {
      'Vocabulary': 0,
      'Understanding': 0,
      'Grammar': 0,
      'Culture': 0,
    },
  });

  final String name;
  final Map<String, MemoryCard> cards;
  final int chats;
  final int capsules;
  final DateTime? lastSessionAt;

  /// 0..1 par compétence.
  final Map<String, double> skills;

  /// Mots solides : revus avec succès au moins une fois.
  int get wordsRemembered => cards.values.where((c) => c.repetitions > 0).length;

  /// Progression dans le niveau A1 (objectif indicatif : 150 mots).
  double get levelProgress => (wordsRemembered / 150).clamp(0, 1).toDouble();

  int get dueCount => SpacedRepetition.dueToday(cards.values.toList(), max: 99).length;

  int daysAway(DateTime now) =>
      lastSessionAt == null ? 0 : now.difference(lastSessionAt!).inDays;

  LearnerState copyWith({
    String? name,
    Map<String, MemoryCard>? cards,
    int? chats,
    int? capsules,
    DateTime? lastSessionAt,
    Map<String, double>? skills,
  }) =>
      LearnerState(
        name: name ?? this.name,
        cards: cards ?? this.cards,
        chats: chats ?? this.chats,
        capsules: capsules ?? this.capsules,
        lastSessionAt: lastSessionAt ?? this.lastSessionAt,
        skills: skills ?? this.skills,
      );
}

class LearnerStore extends ValueNotifier<LearnerState> {
  LearnerStore() : super(const LearnerState());

  void setName(String? name) {
    if (name != null && name.isNotEmpty) value = value.copyWith(name: name.split(' ').first);
  }

  /// Enregistre une réponse : met à jour la carte mémoire (SM-2) et la
  /// compétence travaillée.
  void recordAnswer({
    required String id,
    required String kabyle,
    required String translation,
    required bool correct,
    bool firstTry = true,
    String skill = 'Vocabulary',
  }) {
    final cards = Map<String, MemoryCard>.from(value.cards);
    final card = cards[id] ??
        MemoryCard(id: id, kabyle: kabyle, translation: translation);
    SpacedRepetition.review(card, correct ? (firstTry ? 5 : 3) : 1);
    cards[id] = card;

    final skills = Map<String, double>.from(value.skills);
    final delta = correct ? 0.02 : 0.0;
    skills[skill] = ((skills[skill] ?? 0) + delta).clamp(0, 1).toDouble();
    value = value.copyWith(cards: cards, skills: skills);
  }

  void finishSession({bool withCapsule = false}) {
    final skills = Map<String, double>.from(value.skills);
    if (withCapsule) {
      skills['Culture'] = ((skills['Culture'] ?? 0) + 0.03).clamp(0, 1).toDouble();
    }
    value = value.copyWith(
      lastSessionAt: DateTime.now(),
      capsules: value.capsules + (withCapsule ? 1 : 0),
      skills: skills,
    );
  }

  void recordChat() {
    final skills = Map<String, double>.from(value.skills);
    skills['Understanding'] =
        ((skills['Understanding'] ?? 0) + 0.01).clamp(0, 1).toDouble();
    value = value.copyWith(chats: value.chats + 1, skills: skills);
  }
}

final learnerStore = LearnerStore();
