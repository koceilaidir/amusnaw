import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
import '../../theme/filigree.dart';
import '../../widgets/common.dart';
import '../../theme/mark.dart';
import '../../widgets/content_cards.dart';
import '../culture/culture_screen.dart';
import '../exercise/exercise_screen.dart';
import '../learn/learn_screen.dart';
import '../progress/progress_screen.dart';
import '../onboarding/account_dialog.dart';
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

/// Les deux espaces de l'app : apprendre avec le programme, ou discuter librement.
enum ChatMode { learn, talk }

/// Exemples proposés sous le champ de saisie, dans « Discuter ».
/// Pas d'onglets : on demande simplement ce qu'on veut (« traduis… », « corrige… »).
const _talkExamples = ['Azul ! Amek telliḍ ?', 'Traduis : bonjour, je m’appelle Koceila', 'Corrige : isem-inu Koceila'];

/// Une discussion de l'espace « Discuter » a un identifiant qui commence par « t- ».
ChatMode modeOf(Conversation c) => c.id.startsWith('t-') ? ChatMode.talk : ChatMode.learn;

/// Écran principal : l'app s'ouvre toujours ici, sur le chat avec le prof.
/// Menu en haut à gauche (tiroir), apparence (clair/sombre) en haut à droite.
class TutorChatScreen extends StatefulWidget {
  const TutorChatScreen({super.key, this.initialMode});

  /// Choisi sur l'écran d'accueil ; sinon on reprend le dernier espace utilisé.
  final ChatMode? initialMode;

  @override
  State<TutorChatScreen> createState() => _TutorChatScreenState();
}

class _TutorChatScreenState extends State<TutorChatScreen> {
  static const _topics = ['Une chanson kabyle', 'Yennayer', 'Le village', 'Les prénoms amazighs'];

  final _scaffold = GlobalKey<ScaffoldState>();
  // Ordinateur : menu de gauche ouvert ou rangé (retenu d'une visite à l'autre)
  bool _menuOpen = true;
  final _input = TextEditingController();
  // Le clavier ne s'ouvre que si l'élève touche le champ de saisie.
  final _inputFocus = FocusNode();
  final _scroll = ScrollController();
  late ChatMode _mode = widget.initialMode ?? ChatMode.learn;
  late Conversation _conv = _blank(_mode);
  // Programme A1 (unités et avancement), venu du serveur
  List<Map<String, dynamic>> _units = const [];
  int? _currentUnit;
  // Réponses rapides proposées par le serveur après la dernière réponse du prof
  List<String> _suggestions = const [];
  // Visiteur sans compte (site web) : on lui propose un compte après quelques messages
  bool _guest = false;
  late Future<TodayContent> _today = contentRepository.today();
  bool _sending = false;

  List<ChatMsg> get _messages => _conv.messages;

  static Conversation _blank([ChatMode mode = ChatMode.learn]) => Conversation(
        id: '${mode == ChatMode.talk ? 't-' : ''}${DateTime.now().microsecondsSinceEpoch}',
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
    authService.isGuest().then((g) {
      if (mounted) setState(() => _guest = g);
    });
    SharedPreferences.getInstance().then((prefs) {
      if (!mounted) return;
      setState(() {
        _menuOpen = prefs.getBool('menu_open') ?? true;
        if (widget.initialMode == null && prefs.getString('chat_mode') == 'talk' && _messages.isEmpty) {
          _mode = ChatMode.talk;
          _conv = _blank(_mode);
        }
      });
      if (widget.initialMode != null) prefs.setString('chat_mode', widget.initialMode!.name);
    });
  }

  /// Passe d'un espace à l'autre (Apprendre / Discuter) : nouvelle discussion vide.
  void _setMode(ChatMode m) {
    if (m == _mode) return;
    setState(() {
      _mode = m;
      _conv = _blank(m);
      _suggestions = const [];
    });
    SharedPreferences.getInstance().then((prefs) => prefs.setString('chat_mode', m.name));
    _dropFocus();
  }


  Future<void> _maybeOfferAccount() async {
    if (!_guest || !authService.googleEnabled) return;
    final prefs = await SharedPreferences.getInstance();
    final n = (prefs.getInt('guest_messages') ?? 0) + 1;
    await prefs.setInt('guest_messages', n);
    if ((n == 4 || n == 20) && mounted) await _offerAccount();
  }

  Future<void> _offerAccount() async {
    final ok = await showAccountDialog(context);
    if (!ok || !mounted) return;
    setState(() => _guest = false);
    _syncProgress();
    ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ton compte est prêt : ta progression et tes discussions sont gardées.')));
  }

  void _toggleMenu() {
    setState(() => _menuOpen = !_menuOpen);
    SharedPreferences.getInstance().then((prefs) => prefs.setBool('menu_open', _menuOpen));
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
      await _loadUnits();
    } on RefreshException catch (e) {
      // Jeton expiré ou compte supprimé : retour à l'accueil.
      if (e.status == 401 && mounted) await endSession(context);
    } catch (_) {/* hors ligne : on garde les valeurs locales */}
  }

  /// Avancement dans le programme A1 (barre de l'unité, parcours dans le menu).
  Future<void> _loadUnits() async {
    final res = await api.get('/me/progress');
    learnerStore.setLearnedTotal((res['words_learned'] as num).toInt());
    if (!mounted) return;
    setState(() {
      _units = ((res['units'] as List?) ?? const []).cast<Map<String, dynamic>>();
      _currentUnit = (res['current_unit'] as num?)?.toInt();
    });
  }

  void _newChat() {
    setState(() {
      _conv = _blank(_mode);
      _today = contentRepository.today(refresh: true);
    });
  }

  void _openConversation(Conversation c) {
    setState(() {
      _conv = c;
      _mode = modeOf(c);
    });
    _dropFocus();
  }

  Future<void> _send(String raw, {String? intent}) async {
    final text = raw.trim();
    if (text.isEmpty || _sending) return;
    // Dans « Discuter », chaque message dit au serveur ce qu'on attend : discussion, traduction, correction.
    intent ??= _mode == ChatMode.talk ? 'talk' : null;
    _input.clear();
    FocusScope.of(context).unfocus();
    final conv = _conv;
    if (conv.title.isEmpty) conv.title = text.length > 40 ? '${text.substring(0, 40)}…' : text;
    setState(() {
      conv.messages.add(ChatMsg(text, fromTutor: false));
      _sending = true;
      _suggestions = const [];
    });
    _scrollToEnd();
    final reply = ChatMsg('', fromTutor: true);
    var started = false;
    // Affichage mot par mot, régulier : le texte reçu s'ajoute à une réserve,
    // qu'une minuterie révèle doucement (plus vite si la réserve grossit).
    var pending = '';
    var streamDone = false;
    Timer? reveal;
    void tick() {
      if (!mounted || pending.isEmpty) return;
      final words = (pending.length / 80).ceil().clamp(1, 5);
      var cut = 0;
      for (var i = 0; i < words; i++) {
        final m = RegExp(r'^\s*\S+\s?').firstMatch(pending.substring(cut));
        if (m == null) break;
        final end = cut + m.end;
        // pendant la réception, on n'affiche pas un mot peut-être encore incomplet
        if (!streamDone && end >= pending.length && !RegExp(r'\s$').hasMatch(pending)) break;
        cut = end;
      }
      if (cut == 0) return;
      setState(() {
        if (!started) {
          conv.messages.add(reply);
          started = true;
        }
        reply.text += pending.substring(0, cut);
        pending = pending.substring(cut);
      });
      _scrollToEnd(animate: false);
    }

    Future<void> drain() async {
      streamDone = true;
      while (pending.isNotEmpty && mounted) {
        await Future<void>.delayed(const Duration(milliseconds: 30));
      }
      reveal?.cancel();
    }

    try {
      await for (final ev in api.stream('/tutor/chat/stream', {
        'message': text,
        'tz_offset_minutes': DateTime.now().timeZoneOffset.inMinutes,
        if (intent != null) 'intent': intent,
      }).timeout(
        // 2 minutes sans un mot du prof : on arrête d'attendre et on le dit
        const Duration(seconds: 120),
        onTimeout: (sink) {
          sink.addError(ApiException(503, 'timeout'));
          sink.close();
        },
      )) {
        if (!mounted) return;
        switch (ev['type']) {
          case 'delta':
            pending += ev['text'] as String;
            reveal ??= Timer.periodic(const Duration(milliseconds: 32), (_) => tick());
          case 'done':
            await drain(); // on finit d'écrire avant d'afficher les cartes
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
              _suggestions = ((ev['suggestions'] as List?) ?? const []).cast<String>();
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
            _maybeOfferAccount();
            if (_mode == ChatMode.learn) _loadUnits().catchError((_) {});
          case 'error':
            throw ApiException(503, ev['message'] as String? ?? '');
        }
      }
    } catch (e) {
      reveal?.cancel();
      if (pending.isNotEmpty) reply.text += pending;
      if (!mounted) return;
      // 429 : limite de messages atteinte, le serveur explique gentiment pourquoi
      final pause = e is ApiException && e.status == 429;
      final slow = e is ApiException && e.status == 503; // serveur joint, mais le modèle n'a pas répondu
      setState(() {
        if (started && reply.text.isNotEmpty) {
          reply.failed = true; // réponse coupée : on garde ce qui est arrivé
        } else {
          conv.messages.remove(reply);
          conv.messages.add(ChatMsg(
              pause
                  ? 'Tu as beaucoup écrit cette heure-ci : fais une petite pause, je t’attends ensuite.'
                  : slow
                      ? 'Je suis très demandé en ce moment et je n’ai pas pu terminer ma réponse. Réessaie dans un instant.'
                      : 'Je n’arrive pas à joindre le serveur. Vérifie ta connexion et réessaie.',
              fromTutor: true, failed: true));
        }
      });
    } finally {
      reveal?.cancel();
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
      onReview: _review,
      guest: _guest,
      onAccount: _offerAccount,
      docked: wide,
      mode: _mode,
      onMode: _setMode,
      units: _units,
      currentUnit: _currentUnit,
    );
    return Scaffold(
      key: _scaffold,
      backgroundColor: p.bg,
      drawerScrimColor: const Color(0x52141210),
      onDrawerChanged: (_) => WidgetsBinding.instance.addPostFrameCallback((_) => _dropFocus()),
      drawer: wide ? null : menu,
      body: Row(children: [
        if (wide) // grand écran : menu à gauche, qu'on peut ranger
          AnimatedContainer(
            duration: const Duration(milliseconds: 220),
            curve: Curves.easeOutCubic,
            width: _menuOpen ? 288 : 0,
            child: ClipRect(
              child: OverflowBox(
                alignment: Alignment.centerLeft,
                minWidth: 288,
                maxWidth: 288,
                child: menu,
              ),
            ),
          ),
        Expanded(child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [p.bgTop, p.bg],
            stops: const [0, .4],
          ),
        ),
        child: Stack(children: [
          // Filigrane : la plaine à l'accueil du chat, la brume pendant la conversation
          if (empty)
            Aquarelle(Fond.plaine, opacity: .4,
                height: (MediaQuery.sizeOf(context).width * .5625).clamp(220.0, 460.0))
          else
            const Aquarelle(Fond.brume, opacity: .35),
          SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (wide)
                      RoundIconButton(
                        label: _menuOpen ? 'Ranger le menu' : 'Afficher le menu',
                        icon: Icon(CupertinoIcons.sidebar_left, size: 20, color: p.text),
                        onPressed: _toggleMenu,
                      )
                    else
                      RoundIconButton(
                        label: 'Menu',
                        icon: MenuGlyph(color: p.text),
                        onPressed: () {
                          _dropFocus();
                          _scaffold.currentState?.openDrawer();
                        },
                      ),
                    if (wide && _menuOpen) // le logo est déjà dans le menu de gauche
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
              if (_mode == ChatMode.learn && !empty && _currentUnit != null && _currentUnit! < _units.length)
                _UnitBar(unit: _units[_currentUnit!], index: _currentUnit!),
              Expanded(
                child: ReadingWidth(child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  child: empty
                      ? (_mode == ChatMode.talk
                          ? const _TalkHome(key: ValueKey('talk'))
                          : _Home(
                              key: const ValueKey('home'),
                              today: _today,
                              onLearn: () => _send('Je veux apprendre', intent: 'learn'),
                              onTalk: () => _setMode(ChatMode.talk),
                            ))
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
                topics: empty ? (_mode == ChatMode.talk ? _talkExamples : _topics) : _suggestions,
                onSend: () => _send(_input.text),
                onTopic: (t) => _send(t),
                focusNode: _inputFocus,
                hint: _mode == ChatMode.talk
                    ? 'Écris en kabyle, en français, ou les deux…'
                    : (empty ? 'Écris ton message…' : 'Écris ta réponse…'),
                note: _mode == ChatMode.talk ? 'L’IA peut se tromper en kabyle : vérifie les phrases importantes.' : null,
              )),
            ],
          ),
        ),
        ]),
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
                    title: 'Discuter avec l’IA',
                    subtitle: 'En kabyle, en français, traduire, corriger',
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
    return SelectionArea( // texte sélectionnable et copiable, comme sur les autres IA
      child: ListView(
      controller: controller,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 16),
      children: [
        for (final m in messages)
          Padding(padding: const EdgeInsets.only(bottom: 14), child: _Message(m)),
        if (typing)
          Align(
            alignment: Alignment.centerLeft,
            child: Semantics(label: 'Amusnaw écrit', child: _ThinkingMark(color: p.accent)),
          ),
      ],
    ),
    );
  }
}

extension on Widget {
  /// Message de l'élève + bouton « Copier » dessous, aligné à droite.
  Widget withCopy(String text, {bool right = false}) => Column(
        crossAxisAlignment: right ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [this, _CopyButton(text)],
      );
}

/// Petit bouton « Copier » sous un message.
class _CopyButton extends StatelessWidget {
  const _CopyButton(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Semantics(
      label: 'Copier',
      button: true,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () {
          Clipboard.setData(ClipboardData(text: text.replaceAll('**', '')));
          ScaffoldMessenger.of(context)
            ..hideCurrentSnackBar()
            ..showSnackBar(const SnackBar(content: Text('Copié'), duration: Duration(seconds: 1)));
        },
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Icon(CupertinoIcons.doc_on_doc, size: 16, color: p.text2),
        ),
      ),
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
      ).withCopy(m.text, right: true);
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
      if (m.text.isNotEmpty && !m.failed) _CopyButton(m.text),
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
    required this.focusNode,
    this.hint = 'Écris ton message…',
    this.note,
  });
  final TextEditingController controller;
  final FocusNode focusNode;
  final String hint;
  final String? note;
  final bool sending;
  final List<String> topics;
  final VoidCallback onSend;
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
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(left: 10, bottom: 2),
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
                    hintText: hint,
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
        if (note != null) ...[
          const SizedBox(height: 8),
          Text(note!, textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: p.text2)),
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
    required this.onReview,
    this.guest = false,
    this.onAccount,
    this.docked = false,
    required this.mode,
    required this.onMode,
    this.units = const [],
    this.currentUnit,
  });
  final ChatMode mode;
  final ValueChanged<ChatMode> onMode;
  final List<Map<String, dynamic>> units;
  final int? currentUnit;
  final bool docked;
  final bool guest;
  final VoidCallback? onAccount;
  final String current;
  final VoidCallback onNewChat, onWordOfDay, onReview;
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
              const SizedBox(height: 16),
              // Les deux espaces : Apprendre (programme A1) ou Discuter (libre, traduire, corriger)
              SizedBox(
                width: double.infinity,
                child: CupertinoSlidingSegmentedControl<ChatMode>(
                  groupValue: mode,
                  backgroundColor: p.fill,
                  thumbColor: p.surface,
                  padding: const EdgeInsets.all(4),
                  onValueChanged: (m) {
                    if (m == null) return;
                    close();
                    onMode(m);
                  },
                  children: {
                    ChatMode.learn: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text('Apprendre', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: p.text)),
                    ),
                    ChatMode.talk: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text('Discuter', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: p.text)),
                    ),
                  },
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () {
                  close();
                  onNewChat();
                },
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
                icon: const Icon(CupertinoIcons.pencil, size: 18),
                label: Text(mode == ChatMode.talk ? 'Nouvelle discussion' : 'Nouvelle conversation'),
              ),
              const SizedBox(height: 10),
              if (mode == ChatMode.learn) ...[
                row(CupertinoIcons.arrow_2_circlepath, 'Réviser mes mots', onTap: onReview),
                row(CupertinoIcons.sun_min, 'Mot du jour', onTap: onWordOfDay),
                row(CupertinoIcons.chart_bar_alt_fill, 'Progression',
                    trailing: '${s.learnedTotal} mot${s.learnedTotal > 1 ? 's' : ''}',
                    onTap: () => onPush(const ProgressScreen())),
                row(CupertinoIcons.house, 'Culture et histoire', onTap: () => onPush(const CultureScreen())),
              ] else ...[
                row(CupertinoIcons.sun_min, 'Mot du jour', onTap: onWordOfDay),
                row(CupertinoIcons.house, 'Culture et histoire', onTap: () => onPush(const CultureScreen())),
              ],
              Container(height: .5, margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 10), color: p.separator),
              Expanded(
                child: ValueListenableBuilder(
                  valueListenable: conversationStore,
                  builder: (context, all, _) {
                    final list = all.where((c) => modeOf(c) == mode).toList();
                    Widget header(String t) => Padding(
                          padding: const EdgeInsets.fromLTRB(10, 4, 10, 6),
                          child: Text(t, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: p.text2)),
                        );
                    return ListView(padding: EdgeInsets.zero, children: [
                      if (mode == ChatMode.learn && units.isNotEmpty) ...[
                        header('Ton parcours A1'),
                        for (var i = 0; i < units.length; i++)
                          _UnitRow(
                            unit: units[i],
                            index: i,
                            current: i == currentUnit,
                            onTap: () {
                              close();
                              onPush(const LearnScreen());
                            },
                          ),
                        const SizedBox(height: 12),
                      ],
                      header('Récents'),
                      if (list.isEmpty)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          child: Text(
                              mode == ChatMode.talk
                                  ? 'Tes discussions apparaîtront ici.'
                                  : 'Tes leçons apparaîtront ici.',
                              style: TextStyle(fontSize: 14, color: p.text2)),
                        ),
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
                    ]);
                  },
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
                      Text(guest ? 'Sans compte' : (s.name.isEmpty ? 'Mon compte' : s.name),
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: p.text)),
                      if (guest && authService.googleEnabled)
                        GestureDetector(
                          onTap: () {
                            close();
                            onAccount?.call();
                          },
                          child: Text('Créer un compte', style: TextStyle(fontSize: 13, color: p.accentText)),
                        )
                      else
                        Text('Niveau A1', style: TextStyle(fontSize: 13, color: p.text2)),
                    ]),
                  ),
                  Semantics(
                    label: 'Réglages',
                    button: true,
                    child: GestureDetector(
                      onTap: () {
                        close();
                        openSettings(context); // page sur téléphone, fenêtre centrée sur ordinateur
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


/// Une unité du parcours A1 dans le menu : coche si finie, numéro sinon, barre si en cours.
class _UnitRow extends StatelessWidget {
  const _UnitRow({required this.unit, required this.index, required this.current, required this.onTap});
  final Map<String, dynamic> unit;
  final int index;
  final bool current;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final total = (unit['total'] as num?)?.toInt() ?? 0;
    final seen = (unit['seen'] as num?)?.toInt() ?? 0;
    final done = total > 0 && seen >= total;
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        decoration: BoxDecoration(
          color: current ? p.fill : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(children: [
          Container(
            width: 26,
            height: 26,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: done ? p.accent : (current ? p.text : p.fill),
              borderRadius: BorderRadius.circular(8),
            ),
            child: done
                ? Icon(CupertinoIcons.checkmark_alt, size: 15, color: p.onAccent)
                : Text('${index + 1}',
                    style: TextStyle(
                        fontSize: 13, fontWeight: FontWeight.w700, color: current ? p.bg : p.text2)),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(unit['title'] as String? ?? '',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                      fontSize: 15,
                      fontWeight: current ? FontWeight.w600 : FontWeight.w400,
                      color: current || done ? p.text : p.text2)),
              if (current && total > 0) ...[
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(2),
                  child: LinearProgressIndicator(
                    value: seen / total,
                    minHeight: 4,
                    backgroundColor: p.separator,
                    color: p.accent,
                  ),
                ),
              ],
            ]),
          ),
          if (current && total > 0) ...[
            const SizedBox(width: 10),
            Text('$seen/$total', style: TextStyle(fontSize: 12, color: p.accentText)),
          ],
        ]),
      ),
    );
  }
}

/// « Apprendre » : l'unité en cours et son avancement, au-dessus de la conversation.
class _UnitBar extends StatelessWidget {
  const _UnitBar({required this.unit, required this.index});
  final Map<String, dynamic> unit;
  final int index;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final total = (unit['total'] as num?)?.toInt() ?? 0;
    final seen = (unit['seen'] as num?)?.toInt() ?? 0;
    final narrow = MediaQuery.sizeOf(context).width < 520;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Flexible(
          child: Text('Unité ${index + 1} · ${unit['title'] ?? ''}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: p.text)),
        ),
        if (total > 0) ...[
          const SizedBox(width: 12),
          SizedBox(
            width: narrow ? 70 : 140,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: seen / total,
                minHeight: 6,
                backgroundColor: p.separator,
                color: p.accent,
              ),
            ),
          ),
          if (!narrow) ...[
            const SizedBox(width: 12),
            Text('$seen mot${seen > 1 ? 's' : ''} sur $total', style: TextStyle(fontSize: 14, color: p.text2)),
          ],
        ],
      ]),
    );
  }
}

/// Accueil de « Discuter » : on parle, et on demande ce qu'on veut.
class _TalkHome extends StatelessWidget {
  const _TalkHome({super.key});

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    const title = 'Parle-moi en kabyle.';
    const text = 'En kabyle, en français, ou en mélangeant les deux. Tu peux aussi me demander de traduire '
        'un texte ou de corriger ton kabyle : demande simplement ce que tu veux.';
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
              Text(title,
                  style: TextStyle(
                      fontSize: 32, fontWeight: FontWeight.w500, letterSpacing: -.8, height: 1.1, color: p.text)),
              const SizedBox(height: 12),
              Text(text, style: TextStyle(fontSize: 17, height: 1.45, color: p.text2)),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}

/// Pendant que le prof réfléchit : l'étoile d'Amusnaw tourne et respire doucement.
class _ThinkingMark extends StatefulWidget {
  const _ThinkingMark({required this.color});
  final Color color;

  @override
  State<_ThinkingMark> createState() => _ThinkingMarkState();
}

class _ThinkingMarkState extends State<_ThinkingMark> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 2400))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _c,
        builder: (context, child) {
          final t = _c.value;
          // un tour complet, ralenti au milieu, avec une respiration (taille et opacité)
          final turn = Curves.easeInOutCubic.transform(t);
          final pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi);
          return Opacity(
            opacity: 0.55 + 0.45 * pulse,
            child: Transform.scale(
              scale: 0.9 + 0.12 * pulse,
              child: Transform.rotate(angle: turn * math.pi * 2, child: child),
            ),
          );
        },
        child: AmusnawMark(size: 26, color: widget.color),
      );
}
