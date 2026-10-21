import 'dart:async';

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
import '../../widgets/dialogs.dart';
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

  /// Connexion par e-mail : adresse (+ prénom), puis code à 6 chiffres reçu par e-mail.
  Future<void> _emailLogin() async {
    final first = await showFields(context, 'Continuer avec un e-mail', 'On t’envoie un code à 6 chiffres.', [
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
    final code = await showFields(context, 'Ton code', 'Envoyé à $email. Regarde aussi dans les spams.', [
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
    final r = await showFields(context, 'Continuer sans compte', null, [('Ton prénom', TextInputType.name)]);
    if (r == null) return;
    final name = r[0];
    await _signIn(() => authService.signInForTesting(name: name.isEmpty ? 'Testeur' : name));
  }

  /// Entrée dans l'app.
  void _startOnboarding() {
    Navigator.of(context).pushReplacement(appRoute((_) => const TutorChatScreen()));
  }

  /// Peut-on commencer sans compte ? (site web, ou version de test de l'app)
  bool get _guestOk => kIsWeb || _testMode;

  /// « Commencer » : on entre tout de suite, sans compte sur le site.
  Future<void> _start() async {
    if (_busy) return;
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

  /// Le bouton « Commencer », puis la connexion pour ceux qui ont déjà un compte.
  Widget _choices(AppPalette p, {required bool wide}) {
    final account = _accountActions(p);
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
      Text('Prêt à commencer ?', style: AppTheme.serif(size: wide ? 42 : 30, color: p.text)),
      const SizedBox(height: 10),
      Text(
          _guestOk
              ? 'Sans compte, tout de suite. Ton prof te guide pas à pas et répond à toutes tes questions, '
                  'en français ou en kabyle.'
              : 'Connecte-toi : ton prof te guide pas à pas et répond à toutes tes questions.',
          style: TextStyle(fontSize: wide ? 17 : 15.5, color: p.text2, height: 1.5)),
      SizedBox(height: wide ? 30 : 22),
      SizedBox(
        height: 56,
        child: FilledButton(
          onPressed: _busy ? null : _start,
          style: FilledButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28))),
          child: _busy
              ? Spinner(size: 22, color: p.onAccent)
              : const Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Text('Commencer'),
                  SizedBox(width: 10),
                  Icon(Icons.arrow_forward_rounded, size: 20),
                ]),
        ),
      ),
      if (account.isNotEmpty) ...[
        SizedBox(height: wide ? 32 : 26),
        Row(children: [
          Expanded(child: Divider(color: p.separator, thickness: .5)),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(_guestOk ? 'Déjà un compte ?' : 'Se connecter',
                style: TextStyle(fontSize: 14, color: p.text2)),
          ),
          Expanded(child: Divider(color: p.separator, thickness: .5)),
        ]),
        const SizedBox(height: 16),
        ...account,
      ],
      const SizedBox(height: 10),
      const _DetectedLanguageCard(),
    ]);
  }

  /// Le paysage kabyle, fondu dans le vert olivier (multiplié, puis une touche de lumière).
  static const _olive = Color(0xFF56662E);
  Widget _greenLandscape() => Positioned.fill(
        child: IgnorePointer(
          child: ExcludeSemantics(
            child: Stack(fit: StackFit.expand, children: [
              Image.asset(Fond.olivier.asset,
                  fit: BoxFit.fitWidth,
                  alignment: Alignment.bottomCenter,
                  color: _olive,
                  colorBlendMode: BlendMode.multiply,
                  errorBuilder: (_, __, ___) => const SizedBox.shrink()),
              Opacity(
                opacity: .22,
                child: Image.asset(Fond.olivier.asset,
                    fit: BoxFit.fitWidth,
                    alignment: Alignment.bottomCenter,
                    errorBuilder: (_, __, ___) => const SizedBox.shrink()),
              ),
            ]),
          ),
        ),
      );

  /// Grand écran : à gauche le panneau olivier avec le paysage, à droite « Commencer ».
  Widget _wideLayout(AppPalette p) => Row(children: [
        Expanded(
          flex: 5,
          child: Container(
            color: _olive,
            child: Stack(fit: StackFit.expand, children: [
              _greenLandscape(),
              Padding(
                padding: const EdgeInsets.all(56),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Row(children: [
                    AmusnawMark(size: 34, color: Color(0xFFF8F6F1)),
                    SizedBox(width: 12),
                    Text('amusnaw',
                        style: TextStyle(
                            fontSize: 22, fontWeight: FontWeight.w600, letterSpacing: -.4, color: Color(0xFFF8F6F1))),
                  ]),
                  const Spacer(flex: 2),
                  Text('Azul.', style: AppTheme.serif(size: 104, color: const Color(0xFFF8F6F1))),
                  const SizedBox(height: 20),
                  const Text('Le kabyle, avec une IA\nqui parle ta langue.',
                      style: TextStyle(fontSize: 30, fontWeight: FontWeight.w600, color: Color(0xFFF8F6F1), height: 1.2)),
                  const SizedBox(height: 14),
                  const Text('Des leçons courtes, des exercices corrigés, et un prof qui répond à toutes tes questions.',
                      style: TextStyle(fontSize: 18, color: Color(0xD1F8F6F1), height: 1.5)),
                  const Spacer(flex: 3),
                  const Text('Kabyle en écriture latine · Tifinagh',
                      style: TextStyle(fontSize: 14, color: Color(0xB3F8F6F1))),
                ]),
              ),
            ]),
          ),
        ),
        Expanded(
          flex: 6,
          child: ColoredBox(
            color: p.bg,
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 56, vertical: 40),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 460),
                  child: _choices(p, wide: true),
                ),
              ),
            ),
          ),
        ),
      ]);

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    if (isWide(context)) return Scaffold(body: _wideLayout(p));
    return Scaffold(
      backgroundColor: p.bg,
      body: CustomScrollView(slivers: [
        SliverToBoxAdapter(
          child: Container(
            color: _olive,
            child: Stack(children: [
              _greenLandscape(),
              Padding(
                padding: EdgeInsets.fromLTRB(24, MediaQuery.paddingOf(context).top + 28, 24, 96),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Row(children: [
                    AmusnawMark(size: 28, color: Color(0xFFF8F6F1)),
                    SizedBox(width: 10),
                    Text('amusnaw',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Color(0xFFF8F6F1))),
                  ]),
                  const SizedBox(height: 26),
                  Text('Azul.', style: AppTheme.serif(size: 64, color: const Color(0xFFF8F6F1))),
                  const SizedBox(height: 10),
                  const Text('Le kabyle, avec une IA qui parle ta langue.',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, height: 1.25, color: Color(0xFFF8F6F1))),
                ]),
              ),
            ]),
          ),
        ),
        SliverSafeArea(
          top: false,
          sliver: SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 26, 20, 24),
            sliver: SliverToBoxAdapter(child: _choices(p, wide: false)),
          ),
        ),
      ]),
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
      builder: (context, lang, _) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(children: [
          Icon(Icons.translate_rounded, color: p.text2, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
                localeController.detected
                    ? '${lang.line} · ${kIsWeb ? 'détectée dans ton navigateur' : 'détectée sur ton téléphone'}'
                    : lang.line,
                style: TextStyle(fontSize: 14, color: p.text2)),
          ),
          TextButton(
            onPressed: () => _pick(context),
            style: TextButton.styleFrom(
              foregroundColor: p.accentText,
              textStyle: const TextStyle(fontFamily: AppTheme.font, fontSize: 14, fontWeight: FontWeight.w600),
            ),
            child: const Text('Changer'),
          ),
        ]),
      ),
    );
  }

  Future<void> _pick(BuildContext context) async {
    final l = await showChoice<TutorLanguage>(
      context,
      'Ton prof explique en',
      {for (final l in supportedTutorLanguages) l: l.label},
      selected: localeController.value,
    );
    if (l != null) localeController.choose(l);
  }
}
