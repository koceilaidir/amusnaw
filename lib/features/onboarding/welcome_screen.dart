import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../core/auth/auth_service.dart';
import '../../core/auth/google_button.dart';
import '../../core/chat/conversation_store.dart';
import '../../core/config.dart';
import '../../core/learning/learner_store.dart';
import '../../core/locale/locale_controller.dart';
import '../../theme/app_theme.dart';
import '../../theme/filigree.dart';
import '../../theme/mark.dart';
import '../../widgets/common.dart';
import '../tutor/tutor_chat_screen.dart';

/// Écran 1 : « Azul. », langue détectée + bouton Changer, connexion rapide.
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  bool _busy = false;
  bool _emailOn = false; // le serveur peut envoyer des codes par e-mail (Brevo)

  StreamSubscription<AuthSession>? _webGoogle;

  @override
  void dispose() {
    _webGoogle?.cancel();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    if (kIsWeb && authService.googleEnabled) {
      // Site web : le bouton officiel de Google renvoie la session ici.
      authService.initGoogleWeb();
      _webGoogle = authService.webGoogleSessions.listen((s) {
        if (!mounted) return;
        learnerStore.setName(s.name);
        conversationStore.syncWithServer();
        _startOnboarding();
      }, onError: (_) => _toast('La connexion Google a échoué. Réessaie.'));
    }
    authService.methods().then((m) {
      if (mounted && m['email'] == true) setState(() => _emailOn = true);
    });
  }

  /// Petite fenêtre avec un ou deux champs ; renvoie les valeurs, ou null si annulé.
  Future<List<String>?> _ask(String title, String? message, List<(String, TextInputType)> fields,
      {String action = 'Continuer'}) {
    final ctrls = [for (final _ in fields) TextEditingController()];
    return showCupertinoDialog<List<String>>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: Text(title),
        content: Column(children: [
          if (message != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(message)),
          for (var i = 0; i < fields.length; i++)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: CupertinoTextField(
                controller: ctrls[i],
                placeholder: fields[i].$1,
                keyboardType: fields[i].$2,
                autofocus: i == 0,
                autocorrect: false,
              ),
            ),
        ]),
        actions: [
          CupertinoDialogAction(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, [for (final c in ctrls) c.text.trim()]),
            child: Text(action),
          ),
        ],
      ),
    );
  }

  /// Connexion par e-mail : adresse (+ prénom), puis code à 6 chiffres reçu par e-mail.
  Future<void> _emailLogin() async {
    final first = await _ask('Continuer avec un e-mail', 'On t’envoie un code à 6 chiffres.', [
      ('Ton adresse e-mail', TextInputType.emailAddress),
      ('Ton prénom (première fois)', TextInputType.name),
    ], action: 'Recevoir le code');
    if (first == null || first[0].isEmpty) return;
    final email = first[0], name = first[1];
    setState(() => _busy = true);
    try {
      await authService.sendEmailCode(email);
    } on AuthException catch (e) {
      _toast(e.message);
      return;
    } catch (_) {
      _toast('Serveur injoignable. Vérifie ta connexion et réessaie.');
      return;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (!mounted) return;
    final code = await _ask('Ton code', 'Envoyé à $email. Regarde aussi dans les spams.', [
      ('Code à 6 chiffres', TextInputType.number),
    ], action: 'Se connecter');
    if (code == null || code[0].isEmpty) return;
    await _signIn(() => authService.signInWithEmailCode(email, code[0], name: name));
  }

  bool get _isIOS =>
      !kIsWeb && defaultTargetPlatform == TargetPlatform.iOS;

  Future<void> _signIn(Future<AuthSession?> Function() method) async {
    setState(() => _busy = true);
    try {
      final session = await method();
      if (!mounted || session == null) return;
      learnerStore.setName(session.name);
      _startOnboarding();
    } on AuthException catch (e) {
      _toast(e.message);
    } catch (_) {
      _toast('Serveur injoignable. Vérifie ta connexion et réessaie.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  bool get _testMode => kDebugMode || kIsWeb || AppConfig.testLogin;

  /// Sans compte : on demande juste un prénom, sans Google ni Apple (utile aussi
  /// sur les téléphones sans services Google). Activé par --dart-define=TEST_LOGIN=true.
  Future<void> _testLogin() async {
    final ctrl = TextEditingController();
    final name = await showCupertinoDialog<String>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Continuer sans compte'),
        content: Padding(
          padding: const EdgeInsets.only(top: 12),
          child: CupertinoTextField(controller: ctrl, placeholder: 'Ton prénom', autofocus: true),
        ),
        actions: [
          CupertinoDialogAction(onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text('Continuer'),
          ),
        ],
      ),
    );
    if (name == null) return;
    await _signIn(() => authService.signInForTesting(name: name.isEmpty ? 'Testeur' : name));
  }

  /// Espace choisi sur une carte (Apprendre par défaut après une simple connexion).
  ChatMode? _pendingMode;

  /// Entrée dans l'app, dans l'espace choisi.
  void _startOnboarding() {
    final mode = _pendingMode;
    Navigator.of(context).pushReplacement(CupertinoPageRoute(
      builder: (_) => TutorChatScreen(initialMode: mode),
    ));
  }

  /// Peut-on commencer sans compte ? (site web, ou version de test de l'app)
  bool get _guestOk => kIsWeb || _testMode;

  /// Carte « Apprendre » ou « Discuter » : on entre tout de suite dans l'espace choisi.
  Future<void> _choose(ChatMode mode) async {
    if (_busy) return;
    _pendingMode = mode;
    if (kIsWeb) {
      // Comme les autres IA : pas de compte pour commencer (prénom demandé plus tard par le prof).
      await _signIn(() => authService.signInForTesting(name: ''));
    } else if (_testMode) {
      await _testLogin();
    } else if (authService.googleEnabled) {
      await _signIn(authService.signInWithGoogle);
    } else if (_isIOS) {
      await _signIn(authService.signInWithApple);
    }
  }

  /// Connexion à un compte existant (Apple, Google, e-mail).
  List<Widget> _accountActions(AppPalette p) => [
        if (_isIOS) ...[
          FilledButton(
            onPressed: _busy ? null : () => _signIn(authService.signInWithApple),
            style: FilledButton.styleFrom(backgroundColor: p.text, foregroundColor: p.bg),
            child: const Text('Continuer avec Apple'),
          ),
          const SizedBox(height: 12),
        ],
        if (authService.googleEnabled) ...[
          GoogleButton(onPressed: _busy ? null : () => _signIn(authService.signInWithGoogle)),
          const SizedBox(height: 12),
        ],
        if (_emailOn) ...[
          OutlinedButton(
            onPressed: _busy ? null : _emailLogin,
            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(52)),
            child: const Text('Continuer avec un e-mail'),
          ),
          const SizedBox(height: 12),
        ],
      ];

  /// « Que veux-tu faire ? » : les deux cartes, puis la connexion pour ceux qui ont un compte.
  Widget _choices(AppPalette p, {required bool wide}) {
    final account = _accountActions(p);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
      Text('Que veux-tu faire ?', style: AppTheme.serif(size: wide ? 40 : 28, color: p.text)),
      const SizedBox(height: 8),
      Text(
          _guestOk
              ? 'Sans compte, tout de suite. Tu pourras en créer un pour garder ta progression.'
              : 'Connecte-toi, puis choisis ton espace.',
          style: TextStyle(fontSize: wide ? 17 : 15, color: p.text2, height: 1.4)),
      SizedBox(height: wide ? 26 : 18),
      _ModeCard(
        tile: p.accent,
        icon: Icon(CupertinoIcons.book, color: p.onAccent, size: 26),
        title: 'Apprendre',
        badge: 'Niveau A1',
        text: wide
            ? 'Un prof IA qui t’explique dans ta langue : leçons courtes, exercices corrigés, révisions au bon moment, progression unité par unité.'
            : 'Leçons, exercices, progression',
        onTap: _busy ? null : () => _choose(ChatMode.learn),
      ),
      const SizedBox(height: 14),
      _ModeCard(
        tile: p.ink,
        icon: Icon(CupertinoIcons.chat_bubble_text, color: p.onInk, size: 26),
        title: 'Discuter avec l’IA',
        text: wide
            ? 'Parle en kabyle, en français ou en mélangeant les deux. Fais traduire un texte, corriger ton kabyle, expliquer une expression.'
            : 'En kabyle, en français, traduire',
        chips: wide ? const ['Traduire', 'Corriger mon kabyle', 'Parler en taqbaylit'] : const [],
        onTap: _busy ? null : () => _choose(ChatMode.talk),
      ),
      if (_busy) ...[
        const SizedBox(height: 16),
        const Center(child: CupertinoActivityIndicator()),
      ],
      if (account.isNotEmpty) ...[
        SizedBox(height: wide ? 30 : 22),
        Text(_guestOk ? 'Déjà un compte ?' : 'Se connecter', style: TextStyle(fontSize: 15, color: p.text2)),
        const SizedBox(height: 10),
        ...account,
      ],
      const SizedBox(height: 6),
      const _DetectedLanguageCard(),
    ]);
  }

  /// Grand écran : à gauche le panneau olivier de la marque, à droite les deux espaces.
  Widget _wideLayout(AppPalette p) => Row(children: [
        Expanded(
          flex: 5,
          child: Container(
            color: const Color(0xFF56662E),
            padding: const EdgeInsets.all(56),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const AmusnawMark(size: 34, color: Color(0xFFF8F6F1)),
                const SizedBox(width: 12),
                Text('amusnaw',
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w600, letterSpacing: -.4, color: Color(0xFFF8F6F1))),
              ]),
              const Spacer(),
              Text('Azul.', style: AppTheme.serif(size: 104, color: const Color(0xFFF8F6F1))),
              const SizedBox(height: 20),
              const Text('Le kabyle, avec une IA\nqui parle ta langue.',
                  style: TextStyle(fontSize: 30, fontWeight: FontWeight.w600, color: Color(0xFFF8F6F1), height: 1.2)),
              const SizedBox(height: 14),
              const Text(
                  'Apprends pas à pas, ou parle directement en taqbaylit : l’IA comprend le mélange de kabyle et de français.',
                  style: TextStyle(fontSize: 18, color: Color(0xD1F8F6F1), height: 1.5)),
              const Spacer(),
              const Text('Kabyle en écriture latine · Tifinagh',
                  style: TextStyle(fontSize: 14, color: Color(0xB3F8F6F1))),
            ]),
          ),
        ),
        Expanded(
          flex: 6,
          child: ColoredBox(
            color: p.bg,
            child: Stack(children: [
              // la vallée, en entier, calée en bas
              const Aquarelle(Fond.vallee, opacity: .45, fit: BoxFit.fitWidth),
              Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 56, vertical: 40),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 560),
                    child: _choices(p, wide: true),
                  ),
                ),
              ),
            ]),
          ),
        ),
      ]);

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    if (isWide(context)) return Scaffold(body: _wideLayout(p));
    return Scaffold(
      backgroundColor: p.bg,
      body: Stack(children: [
        const Aquarelle(Fond.olivier, opacity: .5, height: 300, alignment: Alignment(-.25, 1)),
        CustomScrollView(slivers: [
          SliverToBoxAdapter(
            child: Container(
              color: const Color(0xFF56662E),
              padding: EdgeInsets.fromLTRB(24, MediaQuery.paddingOf(context).top + 28, 24, 28),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const AmusnawMark(size: 28, color: Color(0xFFF8F6F1)),
                  const SizedBox(width: 10),
                  Text('amusnaw',
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Color(0xFFF8F6F1))),
                ]),
                const SizedBox(height: 26),
                Text('Azul.', style: AppTheme.serif(size: 64, color: const Color(0xFFF8F6F1))),
                const SizedBox(height: 10),
                const Text('Le kabyle, avec une IA qui parle ta langue.',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, height: 1.25, color: Color(0xFFF8F6F1))),
              ]),
            ),
          ),
          SliverSafeArea(
            top: false,
            sliver: SliverPadding(
              padding: const EdgeInsets.fromLTRB(18, 22, 18, 20),
              sliver: SliverToBoxAdapter(child: _choices(p, wide: false)),
            ),
          ),
        ]),
      ]),
    );
  }
}

/// Grande carte d'un espace (Apprendre / Discuter), comme sur la maquette.
class _ModeCard extends StatelessWidget {
  const _ModeCard({
    required this.tile,
    required this.icon,
    required this.title,
    required this.text,
    required this.onTap,
    this.badge,
    this.chips = const [],
  });
  final Color tile;
  final Widget icon;
  final String title, text;
  final String? badge;
  final List<String> chips;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Semantics(
      button: true,
      label: title,
      child: Material(
        color: p.surface,
        borderRadius: BorderRadius.circular(24),
        child: InkWell(
          borderRadius: BorderRadius.circular(24),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.fromLTRB(20, 20, 18, 20),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: p.separator, width: .5),
              boxShadow: p.shadow,
            ),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                width: 52,
                height: 52,
                alignment: Alignment.center,
                decoration: BoxDecoration(color: tile, borderRadius: BorderRadius.circular(16)),
                child: icon,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Wrap(crossAxisAlignment: WrapCrossAlignment.center, spacing: 10, runSpacing: 4, children: [
                    Text(title, style: TextStyle(fontSize: 21, fontWeight: FontWeight.w600, color: p.text)),
                    if (badge != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(color: p.accentSoft, borderRadius: BorderRadius.circular(999)),
                        child: Text(badge!,
                            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: p.accentText)),
                      ),
                  ]),
                  const SizedBox(height: 6),
                  Text(text, style: TextStyle(fontSize: 15, height: 1.45, color: p.text2)),
                  if (chips.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      for (final c in chips)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                          decoration: BoxDecoration(color: p.fill, borderRadius: BorderRadius.circular(999)),
                          child: Text(c, style: TextStyle(fontSize: 13, color: p.text)),
                        ),
                    ]),
                  ],
                ]),
              ),
              Padding(
                padding: const EdgeInsets.only(top: 14),
                child: Icon(CupertinoIcons.chevron_right, size: 18, color: p.text2),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _DetectedLanguageCard extends StatelessWidget {
  const _DetectedLanguageCard();

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return ValueListenableBuilder(
      valueListenable: localeController,
      builder: (context, lang, _) => Container(
        padding: const EdgeInsets.fromLTRB(16, 12, 12, 12),
        decoration: BoxDecoration(
          color: p.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: p.separator, width: .5),
          boxShadow: p.shadow,
        ),
        child: Row(
          children: [
            Icon(CupertinoIcons.globe, color: p.accent, size: 22),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(lang.line, style: TextStyle(fontSize: 15, color: p.text)),
                  if (localeController.detected)
                    Text(kIsWeb ? 'Détectée dans ton navigateur' : 'Détectée sur ton téléphone',
                        style: TextStyle(fontSize: 13, color: p.text2)),
                ],
              ),
            ),
            CupertinoButton(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              minSize: 34,
              color: p.accentSoft,
              borderRadius: BorderRadius.circular(17),
              onPressed: () => _showLanguageSheet(context),
              child: Text('Changer',
                  style: TextStyle(
                      color: p.accentText,
                      fontSize: 15,
                      fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
    );
  }

  void _showLanguageSheet(BuildContext context) {
    final p = AppPalette.of(context);
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: p.bg,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(14))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: CupertinoListSection.insetGrouped(
            margin: EdgeInsets.zero,
            backgroundColor: p.bg,
            header: const Text('LA LANGUE DANS LAQUELLE TON PROF EXPLIQUE'),
            footer: const Text('D’autres langues arrivent.'),
            children: [
              for (final l in supportedTutorLanguages)
                CupertinoListTile(
                  title: Text(l.label, style: TextStyle(color: p.text)),
                  trailing: l.code == localeController.value.code
                      ? Icon(CupertinoIcons.check_mark, color: p.accent, size: 20)
                      : null,
                  onTap: () {
                    localeController.choose(l);
                    Navigator.of(ctx).pop();
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}
