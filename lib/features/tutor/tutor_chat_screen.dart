import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../content/sample_content.dart';
import '../../core/api/api_client.dart';
import '../../core/auth/auth_service.dart';
import '../../core/auth/session.dart';
import '../../core/chat/conversation_store.dart';
import '../../core/content/content_repository.dart';
import '../../core/learning/learner_store.dart';
import '../../core/learning/review.dart';
import '../../core/locale/locale_controller.dart';
import '../../core/settings/app_settings.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';
import '../../theme/mark.dart';
import '../../widgets/content_cards.dart';
import '../culture/culture_screen.dart';
import '../exercise/exercise_screen.dart';
import '../learn/learn_screen.dart';
import '../progress/progress_screen.dart';
import '../settings/settings_screen.dart';

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

/// Écran principal : l'app s'ouvre toujours ici, sur le chat avec le prof.
/// Menu en haut à gauche (tiroir), apparence (clair/sombre) en haut à droite.
class TutorChatScreen extends StatefulWidget {
  const TutorChatScreen({super.key});

  @override
  State<TutorChatScreen> createState() => _TutorChatScreenState();
}

class _TutorChatScreenState extends State<TutorChatScreen> {
  static const _topics = ['Une chanson kabyle', 'Yennayer', 'Le village', 'Les prénoms amazighs'];

  final _scaffold = GlobalKey<ScaffoldState>();
  final _input = TextEditingController();
  // Le clavier ne s'ouvre que si l'élève touche le champ de saisie.
  final _inputFocus = FocusNode();
  final _scroll = ScrollController();
  late Conversation _conv = _blank();
  late Future<TodayContent> _today = contentRepository.today();
  bool _sending = false;

  List<ChatMsg> get _messages => _conv.messages;

  static Conversation _blank() => Conversation(
        id: DateTime.now().microsecondsSinceEpoch.toString(),
        title: '',
        updatedAt: DateTime.now(),
        messages: [],
      );

  @override
  void initState() {
    super.initState();
    _input.addListener(() => setState(() {}));
    WidgetsBinding.instance.addPostFrameCallback((_) => _dropFocus());
    _syncProgress();
  }

  @override
  void dispose() {
    _input.dispose();
    _inputFocus.dispose();
    _scroll.dispose();
    super.dispose();
  }

  /// Vérifie la session et récupère le nombre de mots appris sur le serveur.
  Future<void> _syncProgress() async {
    try {
      final me = await authService.refresh();
      learnerStore.setName(me['name'] as String?);
      final res = await api.get('/me/progress');
      learnerStore.setLearnedTotal((res['words_learned'] as num).toInt());
    } on RefreshException catch (e) {
      // Jeton expiré ou compte supprimé : retour à l'accueil.
      if (e.status == 401 && mounted) await endSession(context);
    } catch (_) {/* hors ligne : on garde les valeurs locales */}
  }

  void _newChat() {
    setState(() {
      _conv = _blank();
      _today = contentRepository.today(refresh: true);
    });
  }

  void _openConversation(Conversation c) {
    setState(() => _conv = c);
    _dropFocus();
  }

  Future<void> _send(String raw, {String? intent}) async {
    final text = raw.trim();
    if (text.isEmpty || _sending) return;
    _input.clear();
    FocusScope.of(context).unfocus();
    final conv = _conv;
    if (conv.title.isEmpty) conv.title = text.length > 40 ? '${text.substring(0, 40)}…' : text;
    setState(() {
      conv.messages.add(ChatMsg(text, fromTutor: false));
      _sending = true;
    });
    _scrollToEnd();
    final reply = ChatMsg('', fromTutor: true);
    var started = false;
    try {
      await for (final ev in api.stream('/tutor/chat/stream', {
        'message': text,
        'tz_offset_minutes': DateTime.now().timeZoneOffset.inMinutes,
        if (intent != null) 'intent': intent,
      })) {
        if (!mounted) return;
        switch (ev['type']) {
          case 'delta':
            setState(() {
              if (!started) {
                conv.messages.add(reply);
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
                conv.messages.add(reply);
                started = true;
              }
              reply.text = ev['reply'] as String;
              reply.offTopic = ev['off_topic'] == true;
              if (newWords.isNotEmpty && total != null) {
                conv.messages.insert(
                    conv.messages.indexOf(reply),
                    ChatMsg(learnedMessage(localeController.value.code, newWords, total),
                        fromTutor: true, celebration: true));
              }
              for (final b in (ev['blocks'] as List?) ?? const []) {
                if (b is Map<String, dynamic> && _Block.supports(b)) {
                  conv.messages.add(ChatMsg('', fromTutor: true, block: b));
                }
              }
            });
            conversationStore.save(conv);
          case 'error':
            throw ApiException(503, ev['message'] as String? ?? '');
        }
      }
    } catch (e) {
      if (!mounted) return;
      // 429 : limite de messages atteinte, le serveur explique gentiment pourquoi
      final pause = e is ApiException && e.status == 429;
      setState(() {
        if (started && reply.text.isNotEmpty) {
          reply.failed = true; // réponse coupée : on garde ce qui est arrivé
        } else {
          conv.messages.remove(reply);
          conv.messages.add(ChatMsg(
              pause
                  ? 'Tu as beaucoup écrit cette heure-ci : fais une petite pause, je t’attends ensuite.'
                  : 'Je n’arrive pas à joindre le serveur. Vérifie ta connexion et réessaie.',
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
      final target = _scroll.position.maxScrollExtent;
      if (animate) {
        _scroll.animateTo(target, duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      } else {
        _scroll.jumpTo(target);
      }
    });
  }

  // ---------- Navigation (menu, raccourcis) ----------

  /// Ferme le clavier, maintenant et après le retour d'un autre écran
  /// (Flutter redonne sinon le focus au champ de saisie).
  void _dropFocus() {
    _inputFocus.unfocus();
    FocusManager.instance.primaryFocus?.unfocus();
  }

  Future<void> _push(Widget screen) async {
    _dropFocus();
    await Navigator.of(context, rootNavigator: true).push(CupertinoPageRoute(
      builder: (ctx) => Material(
        color: AppPalette.of(ctx).bg,
        child: isWide(ctx) ? ReadingWidth(maxWidth: 820, child: screen) : screen,
      ),
    ));
    if (mounted) WidgetsBinding.instance.addPostFrameCallback((_) => _dropFocus());
  }

  Future<void> _wordOfDay() async {
    final t = await contentRepository.today();
    if (!mounted) return;
    showWordSheet(context, t.word ?? wordOfTheDay);
  }

  void _review() {
    _dropFocus();
    final ex = reviewExercises(learnerStore.value.cards.values.toList());
    if (ex.isEmpty) {
      showCupertinoDialog<void>(
        context: context,
        builder: (ctx) => CupertinoAlertDialog(
          title: const Text('Rien à réviser'),
          content: const Text('Tes mots sont encore frais. Ils reviendront ici au bon moment.'),
          actions: [CupertinoDialogAction(onPressed: () => Navigator.pop(ctx), child: const Text('OK'))],
        ),
      );
      return;
    }
    Navigator.of(context, rootNavigator: true).push(CupertinoPageRoute(
      fullscreenDialog: true,
      builder: (_) => ExerciseScreen(lesson: Lesson(id: 'review', title: 'Révision', subtitle: '', exercises: ex)),
    ));
  }

  void _quickActions() {
    showCupertinoModalPopup<void>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        actions: [
          CupertinoActionSheetAction(
              onPressed: () {
                Navigator.pop(ctx);
                _push(const LearnScreen());
              },
              child: const Text('Leçons')),
          CupertinoActionSheetAction(
              onPressed: () {
                Navigator.pop(ctx);
                _wordOfDay();
              },
              child: const Text('Mot du jour')),
          CupertinoActionSheetAction(
              onPressed: () {
                Navigator.pop(ctx);
                _review();
              },
              child: const Text('Réviser mes mots')),
          CupertinoActionSheetAction(
              onPressed: () {
                Navigator.pop(ctx);
                _push(const CultureScreen());
              },
              child: const Text('Culture et histoire')),
        ],
        cancelButton: CupertinoActionSheetAction(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
      ),
    );
  }

  void _themeMenu() {
    final top = MediaQuery.paddingOf(context).top + 60;
    showGeneralDialog<void>(
      context: context,
      barrierDismissible: true,
      barrierLabel: 'Fermer',
      barrierColor: const Color(0x1F141210),
      transitionDuration: const Duration(milliseconds: 180),
      pageBuilder: (ctx, _, __) => Stack(children: [
        Positioned(top: top, right: 20, child: const _ThemeMenu()),
      ]),
      transitionBuilder: (ctx, anim, _, child) => FadeTransition(
        opacity: anim,
        child: ScaleTransition(
          alignment: Alignment.topRight,
          scale: Tween(begin: .92, end: 1.0).animate(CurvedAnimation(parent: anim, curve: Curves.easeOutCubic)),
          child: child,
        ),
      ),
    );
  }

  // ---------- Interface ----------

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final empty = _messages.isEmpty;
    final wide = isWide(context);
    final menu = _AppDrawer(
      current: _conv.id,
      onNewChat: _newChat,
      onOpen: _openConversation,
      onPush: _push,
      onWordOfDay: _wordOfDay,
      docked: wide,
    );
    return Scaffold(
      key: _scaffold,
      backgroundColor: p.bg,
      drawerScrimColor: const Color(0x52141210),
      onDrawerChanged: (_) => WidgetsBinding.instance.addPostFrameCallback((_) => _dropFocus()),
      drawer: wide ? null : menu,
      body: Row(children: [
        if (wide) menu, // grand écran : menu toujours visible à gauche
        Expanded(child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [p.bgTop, p.bg],
            stops: const [0, .4],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (wide)
                      const SizedBox(width: 44)
                    else
                      RoundIconButton(
                        label: 'Menu',
                        icon: MenuGlyph(color: p.text),
                        onPressed: () {
                          _dropFocus();
                          _scaffold.currentState?.openDrawer();
                        },
                      ),
                    if (wide) // le logo est déjà dans le menu de gauche
                      Flexible(
                        child: Text(empty ? '' : _conv.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: p.text2)),
                      )
                    else
                      Row(mainAxisSize: MainAxisSize.min, children: [
                        AmusnawMark(size: 26, color: p.text),
                        const SizedBox(width: 8),
                        Text('amusnaw',
                            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, letterSpacing: -.3, color: p.text)),
                      ]),
                    RoundIconButton(
                      label: 'Apparence',
                      icon: Icon(p.isDark ? CupertinoIcons.moon : CupertinoIcons.sun_max, size: 20, color: p.text),
                      onPressed: _themeMenu,
                    ),
                  ],
                ),
              ),
              Expanded(
                child: ReadingWidth(child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  child: empty
                      ? _Home(
                          key: const ValueKey('home'),
                          today: _today,
                          onLearn: () => _send('Je veux apprendre', intent: 'learn'),
                          onTalk: () => _send('J’aimerais discuter', intent: 'talk'),
                        )
                      : _MessageList(
                          key: ValueKey(_conv.id),
                          messages: _messages,
                          controller: _scroll,
                          typing: _sending && !_messages.last.fromTutor,
                        ),
                )),
              ),
              ReadingWidth(child: _Composer(
                controller: _input,
                sending: _sending,
                topics: empty ? _topics : const [],
                onSend: () => _send(_input.text),
                onTopic: (t) => _send(t, intent: 'talk'),
                onPlus: _quickActions,
                focusNode: _inputFocus,
              )),
            ],
          ),
        ),
      )),
      ]),
    );
  }
}

// ---------- Accueil : « On apprend, ou on parle d'autre chose ? » ----------

class _Home extends StatelessWidget {
  const _Home({super.key, required this.today, required this.onLearn, required this.onTalk});
  final Future<TodayContent> today;
  final VoidCallback onLearn, onTalk;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final hl = TextStyle(color: p.accentText, fontWeight: FontWeight.w600);
    return ValueListenableBuilder(
      valueListenable: learnerStore,
      builder: (context, s, _) {
        final recent = s.cards.values.map((c) => c.kabyle).toList().reversed.take(2).toList().reversed.toList();
        final List<InlineSpan> recap = recent.isEmpty
            ? const [
                TextSpan(text: 'Je suis Amusnaw, ton prof de kabyle. Un petit pas par jour, sans pression.'),
              ]
            : [
                const TextSpan(text: 'La dernière fois, tu as découvert '),
                TextSpan(text: recent.first, style: hl),
                if (recent.length > 1) ...[const TextSpan(text: ' et '), TextSpan(text: recent.last, style: hl)],
                const TextSpan(text: '.'),
                if (s.learnedTotal > 0) ...[
                  const TextSpan(text: ' Tu as déjà '),
                  TextSpan(
                      text: '${s.learnedTotal} mot${s.learnedTotal > 1 ? 's' : ''}',
                      style: TextStyle(color: p.text, fontWeight: FontWeight.w600)),
                  const TextSpan(text: ' en poche.'),
                ],
              ];
        return LayoutBuilder(
          builder: (context, box) => SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 20),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: box.maxHeight - 32),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AmusnawMark(size: 30, color: p.accent),
                  const SizedBox(height: 12),
                  Text(s.name.isEmpty ? 'Azul.' : 'Azul, ${s.name}.',
                      style: TextStyle(
                          fontSize: 32, fontWeight: FontWeight.w500, letterSpacing: -.8, height: 1.1, color: p.text)),
                  const SizedBox(height: 12),
                  Text.rich(TextSpan(children: recap),
                      style: TextStyle(fontSize: 17, height: 1.45, color: p.text2)),
                  const SizedBox(height: 12),
                  Text('On apprend, ou on parle d’autre chose ?',
                      style: TextStyle(
                          fontSize: 22, fontWeight: FontWeight.w600, height: 1.25, letterSpacing: -.4, color: p.text)),
                  const SizedBox(height: 22),
                  FutureBuilder<TodayContent>(
                    future: today,
                    builder: (context, snap) => _ChoiceCard(
                      tile: p.accent,
                      icon: Icon(CupertinoIcons.book, color: p.onAccent, size: 24),
                      title: 'Apprendre',
                      badge: '8 min',
                      subtitle: snap.data?.lessonTitle ?? 'La leçon du jour',
                      onTap: onLearn,
                    ),
                  ),
                  const SizedBox(height: 10),
                  _ChoiceCard(
                    tile: p.fill,
                    icon: Icon(CupertinoIcons.chat_bubble_2, color: p.text, size: 24),
                    title: 'Discuter',
                    subtitle: 'Culture, histoire, chansons',
                    onTap: onTalk,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ChoiceCard extends StatelessWidget {
  const _ChoiceCard(
      {required this.tile, required this.icon, required this.title, required this.subtitle, required this.onTap, this.badge});
  final Color tile;
  final Widget icon;
  final String title, subtitle;
  final String? badge;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Semantics(
      button: true,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 76),
          padding: const EdgeInsets.fromLTRB(12, 12, 14, 12),
          decoration: cardDecoration(p),
          child: Row(children: [
            Container(
              width: 52,
              height: 52,
              alignment: Alignment.center,
              decoration: BoxDecoration(color: tile, borderRadius: BorderRadius.circular(14)),
              child: icon,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Text(title, style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: p.text)),
                  if (badge != null) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(color: p.accentSoft, borderRadius: BorderRadius.circular(10)),
                      child: Text(badge!,
                          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: p.accentText)),
                    ),
                  ],
                ]),
                const SizedBox(height: 3),
                Text(subtitle,
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 14, color: p.text2)),
              ]),
            ),
            Icon(CupertinoIcons.chevron_right, size: 16, color: p.text2),
          ]),
        ),
      ),
    );
  }
}

// ---------- Conversation ----------

class _MessageList extends StatelessWidget {
  const _MessageList({super.key, required this.messages, required this.controller, required this.typing});
  final List<ChatMsg> messages;
  final ScrollController controller;
  final bool typing;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return ListView(
      controller: controller,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 16),
      children: [
        for (final m in messages)
          Padding(padding: const EdgeInsets.only(bottom: 14), child: _Message(m)),
        if (typing)
          Row(children: [
            AmusnawMark(size: 18, color: p.text2),
            const SizedBox(width: 8),
            Text('Amusnaw écrit…', style: TextStyle(fontSize: 14, color: p.text2)),
          ]),
      ],
    );
  }
}

class _Message extends StatelessWidget {
  const _Message(this.m);
  final ChatMsg m;

  /// **gras** et « guillemets » du prof : mots mis en valeur, en couleur.
  static List<InlineSpan> _rich(String text, TextStyle hl) {
    final spans = <InlineSpan>[];
    final re = RegExp(r'\*\*(.+?)\*\*|«\s?([^»]+?)\s?»');
    var last = 0;
    for (final match in re.allMatches(text)) {
      if (match.start > last) spans.add(TextSpan(text: text.substring(last, match.start)));
      spans.add(TextSpan(text: match.group(1) ?? match.group(2), style: hl));
      last = match.end;
    }
    if (last < text.length) spans.add(TextSpan(text: text.substring(last)));
    return spans;
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    if (m.block != null) return _Block(m.block!);
    if (m.celebration) {
      return Semantics(
        liveRegion: true,
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          decoration: BoxDecoration(color: p.greenSoft, borderRadius: BorderRadius.circular(20)),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(CupertinoIcons.star, color: p.green, size: 22),
            const SizedBox(width: 12),
            Expanded(child: Text(m.text, style: TextStyle(fontSize: 14, height: 1.4, color: p.text))),
          ]),
        ),
      );
    }
    if (!m.fromTutor) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * .75),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: p.bubble,
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(20),
              topRight: Radius.circular(20),
              bottomLeft: Radius.circular(20),
              bottomRight: Radius.circular(6),
            ),
          ),
          child: Text(m.text, style: TextStyle(fontSize: 16, height: 1.4, color: p.text)),
        ),
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text.rich(
        TextSpan(children: _rich(m.text, TextStyle(color: p.accentText, fontWeight: FontWeight.w600))),
        style: TextStyle(fontSize: 16, height: 1.5, color: m.failed ? p.text2 : p.text),
      ),
      if (m.offTopic)
        Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Text('Amusnaw ne parle que de la langue et de la culture kabyles.',
              style: TextStyle(fontSize: 12, color: p.text2)),
        ),
    ]);
  }
}

/// Carte mot / exercice / capsule envoyée par le serveur.
class _Block extends StatelessWidget {
  const _Block(this.b);
  final Map<String, dynamic> b;

  static bool supports(Map<String, dynamic> b) => const {'word', 'exercise', 'capsule'}.contains(b['type']);

  @override
  Widget build(BuildContext context) {
    try {
      return switch (b['type']) {
        'word' => WordCard(word: WordOfTheDay.fromJson(b)),
        'exercise' => InlineExercise(
            exercise: ChoiceExercise.fromJson(b),
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
  }
}

// ---------- Saisie ----------

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.sending,
    required this.topics,
    required this.onSend,
    required this.onTopic,
    required this.onPlus,
    required this.focusNode,
  });
  final TextEditingController controller;
  final FocusNode focusNode;
  final bool sending;
  final List<String> topics;
  final VoidCallback onSend, onPlus;
  final ValueChanged<String> onTopic;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final ready = controller.text.trim().isNotEmpty && !sending;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: p.surface,
            borderRadius: BorderRadius.circular(26),
            border: Border.all(color: p.separator, width: .5),
            boxShadow: p.shadowLg,
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            _Circle(
              label: 'Raccourcis',
              color: p.fill,
              onTap: onPlus,
              child: Icon(CupertinoIcons.add, size: 20, color: p.text),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: TextField(
                  controller: controller,
                  focusNode: focusNode,
                  autofocus: false,
                  minLines: 1,
                  maxLines: 5,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => onSend(),
                  style: TextStyle(fontSize: 16, color: p.text),
                  cursorColor: p.accent,
                  decoration: InputDecoration(
                    isDense: true,
                    border: InputBorder.none,
                    hintText: 'Écris ton message…',
                    hintStyle: TextStyle(color: p.text2, fontSize: 16),
                    contentPadding: const EdgeInsets.symmetric(vertical: 10),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            _Circle(
              label: 'Envoyer',
              color: ready ? p.accent : p.fill,
              onTap: ready ? onSend : null,
              child: sending
                  ? CupertinoActivityIndicator(radius: 8, color: p.text2)
                  : Icon(CupertinoIcons.arrow_up, size: 20, color: ready ? p.onAccent : p.text2),
            ),
          ]),
        ),
        if (topics.isNotEmpty) ...[
          const SizedBox(height: 10),
          SizedBox(
            height: 36,
            child: ShaderMask(
              shaderCallback: (r) => const LinearGradient(
                colors: [Colors.black, Colors.black, Colors.transparent],
                stops: [0, .85, 1],
              ).createShader(r),
              blendMode: BlendMode.dstIn,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: topics.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (_, i) => GestureDetector(
                  onTap: () => onTopic(topics[i]),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: p.surface,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: p.separator, width: .5),
                    ),
                    child: Text(topics[i],
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: p.text)),
                  ),
                ),
              ),
            ),
          ),
        ],
      ]),
    );
  }
}

class _Circle extends StatelessWidget {
  const _Circle({required this.label, required this.color, required this.child, this.onTap});
  final String label;
  final Color color;
  final Widget child;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Semantics(
        label: label,
        button: true,
        enabled: onTap != null,
        child: GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: 40,
            height: 40,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            child: child,
          ),
        ),
      );
}

// ---------- Apparence (en haut à droite) ----------

class _ThemeMenu extends StatelessWidget {
  const _ThemeMenu();

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder(
      valueListenable: appSettings,
      builder: (context, s, _) {
        final p = AppPalette.of(context);
        Widget mode(ThemeMode m, String label) => GestureDetector(
              onTap: () => appSettings.setThemeMode(m),
              child: Container(
                height: 44,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: BoxDecoration(
                  color: s.themeMode == m ? p.fill : Colors.transparent,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Row(children: [
                  Expanded(child: Text(label, style: TextStyle(fontSize: 16, color: p.text))),
                  if (s.themeMode == m) Icon(CupertinoIcons.checkmark_alt, size: 18, color: p.text),
                ]),
              ),
            );
        return Material(
          color: Colors.transparent,
          child: Container(
            width: 236,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: p.panel,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: p.separator, width: .5),
              boxShadow: const [BoxShadow(color: Color(0x38141210), blurRadius: 50, offset: Offset(0, 18))],
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(10, 8, 10, 4),
                child: Text('Apparence', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: p.text2)),
              ),
              mode(ThemeMode.system, 'Automatique'),
              mode(ThemeMode.light, 'Clair'),
              mode(ThemeMode.dark, 'Sombre'),
            ]),
          ),
        );
      },
    );
  }
}

// ---------- Menu (en haut à gauche) ----------

class _AppDrawer extends StatelessWidget {
  const _AppDrawer({
    required this.current,
    required this.onNewChat,
    required this.onOpen,
    required this.onPush,
    required this.onWordOfDay,
    this.docked = false,
  });
  final bool docked;
  final String current;
  final VoidCallback onNewChat, onWordOfDay;
  final ValueChanged<Conversation> onOpen;
  final ValueChanged<Widget> onPush;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    void close() {
      if (!docked) Navigator.of(context).pop();
    }
    Widget row(IconData icon, String label, {String? trailing, required VoidCallback onTap}) => GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () {
            close();
            onTap();
          },
          child: SizedBox(
            height: 48,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(children: [
                Icon(icon, size: 22, color: p.text),
                const SizedBox(width: 14),
                Expanded(child: Text(label, style: TextStyle(fontSize: 16, color: p.text))),
                if (trailing != null) Text(trailing, style: TextStyle(fontSize: 13, color: p.text2)),
              ]),
            ),
          ),
        );

    final content = SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
          child: ValueListenableBuilder(
            valueListenable: learnerStore,
            builder: (context, s, _) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: Row(children: [
                  AmusnawMark(size: 30, color: p.text),
                  const SizedBox(width: 10),
                  Text('amusnaw',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, letterSpacing: -.4, color: p.text)),
                ]),
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: () {
                  close();
                  onNewChat();
                },
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                icon: const Icon(CupertinoIcons.pencil, size: 18),
                label: const Text('Nouvelle conversation'),
              ),
              const SizedBox(height: 10),
              row(CupertinoIcons.book, 'Leçons', trailing: 'A1', onTap: () => onPush(const LearnScreen())),
              row(CupertinoIcons.sun_min, 'Mot du jour', onTap: onWordOfDay),
              row(CupertinoIcons.house, 'Culture et histoire', onTap: () => onPush(const CultureScreen())),
              row(CupertinoIcons.chart_bar_alt_fill, 'Progression',
                  trailing: '${s.learnedTotal} mot${s.learnedTotal > 1 ? 's' : ''}',
                  onTap: () => onPush(const ProgressScreen())),
              Container(height: .5, margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 10), color: p.separator),
              Padding(
                padding: const EdgeInsets.fromLTRB(10, 0, 10, 6),
                child: Text('Récents', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: p.text2)),
              ),
              Expanded(
                child: ValueListenableBuilder(
                  valueListenable: conversationStore,
                  builder: (context, list, _) => list.isEmpty
                      ? Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          child: Text('Tes conversations apparaîtront ici.',
                              style: TextStyle(fontSize: 14, color: p.text2)),
                        )
                      : ListView(padding: EdgeInsets.zero, children: [
                          for (final c in list)
                            GestureDetector(
                              onTap: () {
                                close();
                                onOpen(c);
                              },
                              child: Container(
                                height: 44,
                                padding: const EdgeInsets.symmetric(horizontal: 10),
                                alignment: Alignment.centerLeft,
                                decoration: BoxDecoration(
                                  color: c.id == current ? p.fill : Colors.transparent,
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: Text(c.title,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(fontSize: 16, color: p.text)),
                              ),
                            ),
                        ]),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(6, 8, 0, 0),
                child: Row(children: [
                  Container(
                    width: 40,
                    height: 40,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(color: p.accentSoft, shape: BoxShape.circle),
                    child: Text(s.name.isEmpty ? '?' : s.name.substring(0, 1).toUpperCase(),
                        style: TextStyle(fontWeight: FontWeight.w600, color: p.accentText)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(s.name.isEmpty ? 'Mon compte' : s.name,
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: p.text)),
                      Text('Niveau A1', style: TextStyle(fontSize: 13, color: p.text2)),
                    ]),
                  ),
                  Semantics(
                    label: 'Réglages',
                    button: true,
                    child: GestureDetector(
                      onTap: () {
                        close();
                        Navigator.of(context, rootNavigator: true)
                            .push(CupertinoPageRoute(
                                builder: (ctx) => isWide(ctx)
                                    ? ColoredBox(
                                        color: AppPalette.of(ctx).bg,
                                        child: const ReadingWidth(maxWidth: 820, child: SettingsScreen()))
                                    : const SettingsScreen()));
                      },
                      child: Container(
                        width: 44,
                        height: 44,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(color: p.fill, shape: BoxShape.circle),
                        child: Icon(CupertinoIcons.gear, size: 20, color: p.text),
                      ),
                    ),
                  ),
                ]),
              ),
            ]),
          ),
        ),
      );
    if (docked) {
      return Container(
        width: 288,
        decoration: BoxDecoration(
          color: p.panel,
          border: Border(right: BorderSide(color: p.separator, width: .5)),
        ),
        child: content,
      );
    }
    return Drawer(
      width: 318,
      backgroundColor: p.panel,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.horizontal(right: Radius.circular(30))),
      child: content,
    );
  }
}
