import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';

/// Un message affiché dans le chat.
class ChatMsg {
  ChatMsg(this.text,
      {required this.fromTutor, this.offTopic = false, this.failed = false, this.celebration = false, this.block});

  /// Modifiable : la réponse du prof s'écrit au fur et à mesure (streaming).
  String text;
  final bool fromTutor;
  bool offTopic;
  bool failed;

  /// Félicitations (nouveaux mots appris), affichées par l'app.
  final bool celebration;

  /// Carte construite par le serveur (word, exercise, capsule).
  final Map<String, dynamic>? block;

  Map<String, dynamic> toJson() => {
        't': text,
        'tutor': fromTutor,
        if (offTopic) 'off': true,
        if (celebration) 'cel': true,
        if (block != null) 'block': block,
      };

  factory ChatMsg.fromJson(Map<String, dynamic> j) => ChatMsg(
        (j['t'] as String?) ?? '',
        fromTutor: j['tutor'] == true,
        offTopic: j['off'] == true,
        celebration: j['cel'] == true,
        block: (j['block'] as Map?)?.cast<String, dynamic>(),
      );
}

class Conversation {
  Conversation({required this.id, required this.title, required this.updatedAt, required this.messages});
  final String id;
  String title;
  DateTime updatedAt;
  final List<ChatMsg> messages;

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'at': updatedAt.toIso8601String(),
        'm': [for (final m in messages) if (!m.failed && (m.text.isNotEmpty || m.block != null)) m.toJson()],
      };

  factory Conversation.fromJson(Map<String, dynamic> j) => Conversation(
        id: j['id'] as String,
        title: (j['title'] as String?) ?? '',
        updatedAt: DateTime.tryParse((j['at'] as String?) ?? '') ?? DateTime.now(),
        messages: [
          for (final m in (j['m'] as List? ?? const []).cast<Map<String, dynamic>>()) ChatMsg.fromJson(m),
        ],
      );
}

/// Conversations récentes, gardées sur le téléphone (menu « Récents »).
class ConversationStore extends ValueNotifier<List<Conversation>> {
  ConversationStore() : super(const []);

  static const _key = 'conversations_v1';
  static const _max = 20;
  SharedPreferences? _prefs;

  void load(SharedPreferences prefs) {
    _prefs = prefs;
    final raw = prefs.getString(_key);
    if (raw == null) return;
    try {
      value = [
        for (final c in (jsonDecode(raw) as List).cast<Map<String, dynamic>>()) Conversation.fromJson(c),
      ];
    } catch (_) {/* format inattendu : on repart de zéro */}
  }

  /// Enregistre (ou met à jour) une conversation et la remonte en tête.
  void save(Conversation c) {
    if (c.messages.where((m) => !m.fromTutor).isEmpty) return; // rien dit : pas d'historique
    c.updatedAt = DateTime.now();
    final list = [c, ...value.where((x) => x.id != c.id)].take(_max).toList();
    value = list;
    _persist();
    // Copie sur le serveur : la discussion se retrouve sur un autre appareil.
    final j = c.toJson();
    api.put('/me/conversations/${c.id}', {'title': j['title'], 'm': j['m']}).catchError((_) => <String, dynamic>{});
  }

  void _persist() => _prefs?.setString(_key, jsonEncode([for (final x in value) x.toJson()]));

  /// Récupère les discussions enregistrées sur le serveur (après connexion,
  /// ou à l'ouverture) et les fusionne avec celles de l'appareil.
  Future<void> syncWithServer() async {
    try {
      final list = await api.getAny('/me/conversations') as List;
      final remote = [for (final c in list.cast<Map<String, dynamic>>()) Conversation.fromJson(c)];
      final byId = {for (final c in value) c.id: c};
      for (final r in remote) {
        final local = byId[r.id];
        if (local == null || r.updatedAt.isAfter(local.updatedAt)) byId[r.id] = r;
      }
      final merged = byId.values.toList()..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
      value = merged.take(_max).toList();
      _persist();
    } catch (_) {/* hors ligne : on garde l'appareil */}
  }

  Future<void> clear() async {
    value = const [];
    await _prefs?.remove(_key);
  }
}

final conversationStore = ConversationStore();
