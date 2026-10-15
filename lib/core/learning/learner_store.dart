import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'spaced_repetition.dart';

/// État local de l'apprenant, enregistré sur le téléphone (shared_preferences).
/// Le nombre de mots appris fait foi côté serveur et est resynchronisé.
class LearnerState {
  const LearnerState({
    this.name = '',
    this.cards = const {},
    this.chats = 0,
    this.capsules = 0,
    this.lastSessionAt,
    this.learnedTotal = 0,
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

  /// Mots « appris » selon le serveur : découverts un jour, réemployés par
  /// l'élève lui-même un autre jour dans une conversation.
  final int learnedTotal;

  /// 0..1 par compétence.
  final Map<String, double> skills;

  /// Mots solides : revus avec succès au moins une fois.
  int get wordsRemembered => cards.values.where((c) => c.repetitions > 0).length;

  /// Progression dans le niveau A1 (objectif indicatif : 150 mots appris).
  double get levelProgress => (learnedTotal / 150).clamp(0, 1).toDouble();

  int get dueCount => SpacedRepetition.dueToday(cards.values.toList(), max: 99).length;

  int daysAway(DateTime now) =>
      lastSessionAt == null ? 0 : now.difference(lastSessionAt!).inDays;

  Map<String, dynamic> toJson() => {
        'name': name,
        'cards': [for (final c in cards.values) c.toJson()],
        'chats': chats,
        'capsules': capsules,
        'lastSessionAt': lastSessionAt?.toIso8601String(),
        'learnedTotal': learnedTotal,
        'skills': skills,
      };

  factory LearnerState.fromJson(Map<String, dynamic> j) {
    const empty = LearnerState();
    return LearnerState(
      name: (j['name'] as String?) ?? '',
      cards: {
        for (final c in (j['cards'] as List? ?? const []).cast<Map<String, dynamic>>())
          c['id'] as String: MemoryCard.fromJson(c),
      },
      chats: (j['chats'] as num?)?.toInt() ?? 0,
      capsules: (j['capsules'] as num?)?.toInt() ?? 0,
      lastSessionAt: DateTime.tryParse((j['lastSessionAt'] as String?) ?? ''),
      learnedTotal: (j['learnedTotal'] as num?)?.toInt() ?? 0,
      skills: {
        ...empty.skills,
        for (final e in ((j['skills'] as Map?) ?? const {}).entries)
          e.key as String: (e.value as num).toDouble(),
      },
    );
  }

  LearnerState copyWith({
    String? name,
    Map<String, MemoryCard>? cards,
    int? chats,
    int? capsules,
    DateTime? lastSessionAt,
    int? learnedTotal,
    Map<String, double>? skills,
  }) =>
      LearnerState(
        name: name ?? this.name,
        cards: cards ?? this.cards,
        chats: chats ?? this.chats,
        capsules: capsules ?? this.capsules,
        lastSessionAt: lastSessionAt ?? this.lastSessionAt,
        learnedTotal: learnedTotal ?? this.learnedTotal,
        skills: skills ?? this.skills,
      );
}

class LearnerStore extends ValueNotifier<LearnerState> {
  LearnerStore() : super(const LearnerState());

  static const _key = 'learner_state_v1';
  SharedPreferences? _prefs;

  /// Charge l'état enregistré puis l'enregistre à chaque changement.
  Future<void> load(SharedPreferences prefs) async {
    _prefs = prefs;
    final raw = prefs.getString(_key);
    if (raw != null) {
      try {
        value = LearnerState.fromJson(jsonDecode(raw) as Map<String, dynamic>);
      } catch (_) {/* format inattendu : on repart de zéro */}
    }
    addListener(_save);
  }

  void _save() => _prefs?.setString(_key, jsonEncode(value.toJson()));

  /// Déconnexion ou suppression du compte : on efface tout.
  Future<void> reset() async {
    value = const LearnerState();
    await _prefs?.remove(_key);
  }

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

  void setLearnedTotal(int total) {
    if (total != value.learnedTotal) value = value.copyWith(learnedTotal: total);
  }

  void recordChat() {
    final skills = Map<String, double>.from(value.skills);
    skills['Understanding'] =
        ((skills['Understanding'] ?? 0) + 0.01).clamp(0, 1).toDouble();
    value = value.copyWith(chats: value.chats + 1, skills: skills);
  }
}

final learnerStore = LearnerStore();
