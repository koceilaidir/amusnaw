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

  /// Écran 2 (le prof fait connaissance), puis l'app avec ses onglets.
  void _startOnboarding() {
    Navigator.of(context).pushReplacement(CupertinoPageRoute(
      builder: (_) => const TutorChatScreen(),
    ));
  }

  /// Boutons de connexion (téléphone et grand écran).
  List<Widget> _actions(AppPalette p) => [
    if (_isIOS) ...[
      FilledButton(
        onPressed:
            _busy ? null : () => _signIn(authService.signInWithApple),
        style: FilledButton.styleFrom(
          backgroundColor: p.text,
          foregroundColor: p.bg,
        ),
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
    if (kIsWeb) // sur le site, c'est l'entrée principale : vrai bouton
      FilledButton(
        onPressed: _busy ? null : _testLogin,
        style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
        child: const Text('Commencer sans compte'),
      )
    else if (_testMode || !_emailOn)
    CupertinoButton(
      // Sans compte (prénom seulement) ; la connexion par e-mail viendra plus tard.
      onPressed: _busy ? null : (_testMode ? _testLogin : null),
      child: Text(_testMode ? 'Continuer sans compte' : 'Utiliser un e-mail',
          style: TextStyle(color: p.accentText, fontSize: 17)),
    ),
      ];

  /// Grand écran : à gauche le panneau olivier de la marque, à droite la connexion.
  Widget _wideLayout(AppPalette p) => Row(children: [
        Expanded(
          flex: 5,
          child: Container(
            color: const Color(0xFF56662E),
            child: Stack(children: [
              Padding(
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
              Text('Azul.', style: AppTheme.serif(size: 96, color: const Color(0xFFF8F6F1))),
              const SizedBox(height: 16),
              const Text('Je suis Amusnaw, ton prof de kabyle.',
                  style: TextStyle(fontSize: 30, fontWeight: FontWeight.w600, color: Color(0xFFF8F6F1), height: 1.2)),
              const SizedBox(height: 12),
              const Text('La langue, la culture et l’histoire — un petit pas par jour.',
                  style: TextStyle(fontSize: 19, color: Color(0xCCF8F6F1), height: 1.45)),
              const Spacer(),
              const Text('Kabyle en écriture latine · Tifinagh',
                  style: TextStyle(fontSize: 14, color: Color(0x99F8F6F1))),
            ]),
          ),
            ]),
          ),
        ),
        Expanded(
          flex: 4,
          child: ColoredBox(
            color: p.bg,
            child: Stack(children: [
              // la vallée, en entier, calée en bas
              const Aquarelle(Fond.vallee, opacity: .45, fit: BoxFit.fitWidth),
              Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(40),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 400),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                    Text('Commencer', style: AppTheme.serif(size: 40, color: p.text)),
                    const SizedBox(height: 8),
                    Text('Huit minutes par jour, à ton rythme.',
                        style: TextStyle(fontSize: 17, color: p.text2)),
                    const SizedBox(height: 28),
                    const _DetectedLanguageCard(),
                    const SizedBox(height: 28),
                    ..._actions(p),
                  ]),
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
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [p.bgTop, p.bg],
            stops: const [0, .45],
          ),
        ),
        child: Stack(
        children: [
          const Aquarelle(Fond.olivier, opacity: .5, height: 300, alignment: Alignment(-.25, 1)),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      width: 64,
                      height: 64,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: p.ink,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: AmusnawMark(size: 48, color: p.onInk),
                    ),
                  ),
                  const SizedBox(height: 56),
                  Text('Azul.', style: AppTheme.serif(size: 72, color: p.text)),
                  const SizedBox(height: 12),
                  Text('Je suis Amusnaw, ton prof de kabyle.',
                      style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                          color: p.text)),
                  const SizedBox(height: 8),
                  Text('La langue, la culture et l’histoire — un petit pas par jour.',
                      style: TextStyle(fontSize: 17, color: p.text2, height: 1.45)),
                  const SizedBox(height: 28),
                  const _DetectedLanguageCard(),
                  const Spacer(),
                  ..._actions(p),
                ],
              ),
            ),
          ),
        ],
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
