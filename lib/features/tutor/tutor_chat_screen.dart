import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/learning/learner_store.dart';
import '../../core/locale/locale_controller.dart';
import '../../theme/app_theme.dart';
import '../../theme/filigree.dart';
import '../../content/sample_content.dart';
import '../../widgets/common.dart';
import '../../widgets/content_cards.dart';

class _Msg {
  _Msg(this.text,
      {required this.fromTutor,
      this.offTopic = false,
      this.failed = false,
      this.celebration = false,
      this.block});

  /// Élément interactif construit par le serveur à partir de la base vérifiée
  /// (type : word, exercise, capsule). Les types inconnus sont ignorés, ce qui
  /// permet d'en ajouter côté serveur sans casser cette version de l'app.
  final Map<String, dynamic>? block;

  /// Modifiable : la réponse du prof s'écrit au fur et à mesure (streaming).
  String text;
  final bool fromTutor;
  bool offTopic;
  bool failed;

  /// Message de félicitations (nouveaux mots appris), affiché par l'app.
  final bool celebration;
}

/// « Félicitations… le nombre total est de : N », dans la langue de l'élève.
String learnedMessage(String lang, List<String> words, int total) {
  final w = words.map((e) => '« $e »').join(', ');
  final en = words.map((e) => '“$e”').join(', ');
  switch (lang) {
    case 'fr':
      return 'Félicitations ! Tu as réutilisé $w. Ton nombre de mots appris a augmenté : le total est de $total.';
    case 'ar':
      return 'تهانينا! استعملت من جديد $en. ازداد عدد الكلمات التي تعلّمتها: المجموع $total.';
    case 'es':
      return '¡Enhorabuena! Has vuelto a usar $en. Tu número de palabras aprendidas ha aumentado: el total es $total.';
    case 'de':
      return 'Glückwunsch! Du hast $en wieder benutzt. Deine Zahl gelernter Wörter ist gestiegen: insgesamt $total.';
    default:
      return 'Congratulations! You used $en again. Your number of learned words went up: the total is $total.';
  }
}

/// Écran 2 : conversation avec le prof.
/// [onboarding] = premier échange (niveau, objectifs, vécu) avec réponses rapides.
class TutorChatScreen extends StatefulWidget {
  const TutorChatScreen({super.key, this.onboarding = false, this.onDone});

  final bool onboarding;

  /// Appelé quand l'utilisateur quitte l'onboarding (bouton « Continue »).
  final VoidCallback? onDone;

  @override
  State<TutorChatScreen> createState() => _TutorChatScreenState();
}

class _TutorChatScreenState extends State<TutorChatScreen> {
  static const _greetings = {
    'en': "That's “hello” in Kabyle. How's your day going?",
    'fr': "C'est « bonjour » en kabyle. Comment se passe ta journée ?",
    'ar': 'هذه تعني «مرحبًا» بالقبائلية. كيف يمضي يومك؟',
    'es': 'Es «hola» en cabilio. ¿Qué tal tu día?',
    'de': 'Das heißt „Hallo“ auf Kabylisch. Wie läuft dein Tag?',
  };

  static const _quickReplies = [
    'Talk with my family',
    'Understand songs',
    'Culture & history',
    'Start from zero',
  ];

  final _messages = <_Msg>[];
  final _input = TextEditingController();
  final _scroll = ScrollController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    final name = learnerStore.value.name;
    final lang = localeController.value.code;
    _messages.add(_Msg(
      'Azul${name.isEmpty ? '' : ', $name'}! ${_greetings[lang] ?? _greetings['en']}',
      fromTutor: true,
    ));
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _input.text).trim();
    if (text.isEmpty || _sending) return;
    _input.clear();
    setState(() {
      _messages.add(_Msg(text, fromTutor: false));
      _sending = true;
    });
    _scrollToEnd();
    // La réponse du prof s'affiche mot par mot pendant qu'elle est générée.
    final reply = _Msg('', fromTutor: true);
    var started = false;
    try {
      await for (final ev in api.stream('/tutor/chat/stream', {
        'message': text,
        'tz_offset_minutes': DateTime.now().timeZoneOffset.inMinutes,
      })) {
        if (!mounted) return;
        switch (ev['type']) {
          case 'delta':
            setState(() {
              if (!started) {
                _messages.add(reply);
                started = true;
              }
              reply.text += ev['text'] as String;
            });
            _scrollToEnd(animate: false);
          case 'done':
            learnerStore.recordChat();
            final learned = (ev['learned'] as Map?) ?? const {};
            final newWords = ((learned['new'] as List?) ?? const []).cast<String>();
            final total = (learned['total'] as num?)?.toInt();
            if (total != null) learnerStore.setLearnedTotal(total);
            setState(() {
              if (!started) {
                _messages.add(reply);
                started = true;
              }
              reply.text = ev['reply'] as String;
              reply.offTopic = ev['off_topic'] == true;
              if (newWords.isNotEmpty && total != null) {
                // Les félicitations s'affichent juste avant la réponse du prof.
                _messages.insert(_messages.indexOf(reply),
                    _Msg(learnedMessage(localeController.value.code, newWords, total),
                        fromTutor: true, celebration: true));
              }
              for (final b in (ev['blocks'] as List?) ?? const []) {
                if (b is Map<String, dynamic> && _BlockView.supports(b)) {
                  _messages.add(_Msg('', fromTutor: true, block: b));
                }
              }
            });
          case 'error':
            throw ApiException(503, ev['message'] as String? ?? '');
        }
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        if (started && reply.text.isNotEmpty) {
          reply.failed = true; // réponse coupée : on garde ce qui est arrivé
        } else {
          _messages.remove(reply);
          _messages.add(_Msg('I couldn’t reach your tutor. Check your connection and try again.',
              fromTutor: true, failed: true));
        }
      });
    } finally {
      if (mounted) setState(() => _sending = false);
      _scrollToEnd();
    }
  }

  void _scrollToEnd({bool animate = true}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      final target = _scroll.position.maxScrollExtent + 80;
      if (animate) {
        _scroll.animateTo(target, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      } else {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final chatBg = Theme.of(context).brightness == Brightness.dark ? Colors.black : Colors.white;
    final showQuick = widget.onboarding && _messages.length <= 2;

    return CupertinoPageScaffold(
      backgroundColor: chatBg,
      navigationBar: CupertinoNavigationBar(
        backgroundColor: p.surface.withValues(alpha: .94),
        middle: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            TutorAvatar(size: 28),
            SizedBox(width: 8),
            Text('Amusnaw'),
          ],
        ),
        trailing: widget.onboarding && widget.onDone != null
            ? CupertinoButton(
                padding: EdgeInsets.zero,
                onPressed: widget.onDone,
                child: Text('Continue', style: TextStyle(color: p.accent, fontWeight: FontWeight.w600)),
              )
            : null,
      ),
      child: SafeArea(
        child: Stack(
          children: [
            Center(child: Rosette(size: 300, opacity: .05, color: p.accent)),
            Column(
              children: [
                Expanded(
                  child: ListView(
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                    children: [
                      for (final m in _messages) _Bubble(m),
                      if (showQuick)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Wrap(
                            spacing: 6,
                            runSpacing: 6,
                            children: [
                              for (final q in _quickReplies)
                                _Chip(label: q, onTap: () => _send(q)),
                            ],
                          ),
                        ),
                      // « Amusnaw is writing… » jusqu'au premier mot de la réponse
                      if (_sending && !_messages.last.fromTutor) const _Typing(),
                    ],
                  ),
                ),
                _InputBar(controller: _input, onSend: _send, enabled: !_sending),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble(this.m);
  final _Msg m;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    if (m.celebration) return _Celebration(m.text);
    if (m.block != null) return _BlockView(m.block!);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = m.fromTutor ? (isDark ? const Color(0xFF26252A) : const Color(0xFFE9E9EB)) : p.accent;
    final fg = m.fromTutor ? p.text : p.onAccent;
    return Align(
      alignment: m.fromTutor ? Alignment.centerLeft : Alignment.centerRight,
      child: Column(
        crossAxisAlignment: m.fromTutor ? CrossAxisAlignment.start : CrossAxisAlignment.end,
        children: [
          Container(
            margin: const EdgeInsets.symmetric(vertical: 3),
            constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .78),
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 8),
            decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(18)),
            child: Text(m.text,
                style: TextStyle(color: m.failed ? p.text2 : fg, fontSize: 16, height: 1.35)),
          ),
          if (m.offTopic)
            Padding(
              padding: const EdgeInsets.only(left: 12, bottom: 4),
              child: Text('Stays on topic · language & culture only',
                  style: TextStyle(fontSize: 12, color: p.text2)),
            ),
        ],
      ),
    );
  }
}

/// Carte mot / exercice / capsule sous la réponse du prof.
class _BlockView extends StatelessWidget {
  const _BlockView(this.b);
  final Map<String, dynamic> b;

  static bool supports(Map<String, dynamic> b) =>
      const {'word', 'exercise', 'capsule'}.contains(b['type']);

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardBg = isDark ? const Color(0xFF1C1C1E) : p.bg;
    final Widget child;
    try {
      child = switch (b['type']) {
        'word' => WordCard(word: WordOfTheDay.fromJson(b), caption: 'New word', compact: true, color: cardBg),
        'exercise' => InlineExercise(
            exercise: ChoiceExercise.fromJson(b),
            color: cardBg,
            onCorrect: () {
              final ex = ChoiceExercise.fromJson(b);
              final word = ex.hasBlank ? ex.answer : ex.before;
              api.post('/learning/seen', {
                'words': [word],
              }).catchError((_) => <String, dynamic>{});
              learnerStore.recordAnswer(
                id: ex.id,
                kabyle: word,
                translation: ex.hasBlank ? (ex.translation ?? '') : ex.answer,
                correct: true,
              );
            },
          ),
        'capsule' => CapsuleCard(capsule: CultureCapsule.fromJson(b), showBody: true),
        _ => const SizedBox.shrink(),
      };
    } catch (_) {
      return const SizedBox.shrink(); // bloc mal formé : on n'affiche rien
    }
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .82),
        child: child,
      ),
    );
  }
}

/// Carte de félicitations, centrée, couleur « réussite ».
class _Celebration extends StatelessWidget {
  const _Celebration(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Semantics(
      liveRegion: true,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
        decoration: BoxDecoration(color: p.greenSoft, borderRadius: BorderRadius.circular(16)),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(CupertinoIcons.star_circle_fill, color: p.green, size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Text(text,
                  style: TextStyle(fontSize: 15, height: 1.4, color: p.text, fontWeight: FontWeight.w500)),
            ),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.onTap});
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Semantics(
      button: true,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 13),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border.all(color: p.accent),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Text(label, style: TextStyle(color: p.accent, fontSize: 15)),
        ),
      ),
    );
  }
}

class _Typing extends StatelessWidget {
  const _Typing();

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const CupertinoActivityIndicator(radius: 8),
          const SizedBox(width: 8),
          Text('Amusnaw is writing…', style: TextStyle(color: p.text2, fontSize: 13)),
        ]),
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  const _InputBar({required this.controller, required this.onSend, required this.enabled});
  final TextEditingController controller;
  final Future<void> Function([String?]) onSend;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      color: p.surface.withValues(alpha: .94),
      child: Row(
        children: [
          Expanded(
            child: CupertinoTextField(
              controller: controller,
              placeholder: 'Message in any language',
              minLines: 1,
              maxLines: 5,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => onSend(),
              style: TextStyle(color: p.text, fontSize: 16),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                border: Border.all(color: p.separator),
                borderRadius: BorderRadius.circular(18),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Semantics(
            label: 'Send',
            button: true,
            child: CupertinoButton(
              padding: EdgeInsets.zero,
              minSize: 34,
              onPressed: enabled ? () => onSend() : null,
              child: Icon(CupertinoIcons.arrow_up_circle_fill, size: 34, color: p.accent),
            ),
          ),
        ],
      ),
    );
  }
}
