import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../core/auth/auth_service.dart';
import '../../core/config.dart';
import '../../core/learning/learner_store.dart';
import '../../core/locale/locale_controller.dart';
import '../../theme/app_theme.dart';
import '../../theme/filigree.dart';
import '../home/home_shell.dart';
import '../tutor/tutor_chat_screen.dart';

/// Écran 1 : « Azul. », langue détectée + bouton Changer, connexion rapide.
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  bool _busy = false;

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
      _toast('Server unreachable. Check API_BASE_URL and that the server is running.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _toast(String msg) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  bool get _testMode => kDebugMode || AppConfig.testLogin;

  /// Bêta : on demande juste un prénom, sans Google ni Apple.
  Future<void> _testLogin() async {
    final ctrl = TextEditingController();
    final name = await showCupertinoDialog<String>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Test without an account'),
        content: Padding(
          padding: const EdgeInsets.only(top: 12),
          child: CupertinoTextField(controller: ctrl, placeholder: 'Your first name', autofocus: true),
        ),
        actions: [
          CupertinoDialogAction(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text('Continue'),
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
      builder: (ctx) => TutorChatScreen(
        onboarding: true,
        onDone: () => Navigator.of(ctx).pushReplacement(
          CupertinoPageRoute(builder: (_) => const HomeShell()),
        ),
      ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Scaffold(
      body: Stack(
        children: [
          const Positioned(
              top: -70, right: -120, child: Rosette(size: 360, opacity: .14)),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      width: 60,
                      height: 60,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: p.accent,
                        borderRadius: BorderRadius.circular(15),
                      ),
                      child: Text('ⵣ',
                          style: AppTheme.tifinagh(size: 32, color: p.onAccent)),
                    ),
                  ),
                  const SizedBox(height: 56),
                  Text('Azul.', style: AppTheme.serif(size: 76, color: p.text)),
                  const SizedBox(height: 12),
                  Text("I'm Amusnaw, your Kabyle tutor.",
                      style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                          color: p.text)),
                  const SizedBox(height: 8),
                  Text('Language, culture and history — one small step a day.',
                      style: TextStyle(fontSize: 17, color: p.text2, height: 1.45)),
                  const SizedBox(height: 28),
                  const _DetectedLanguageCard(),
                  const Spacer(),
                  if (_isIOS) ...[
                    FilledButton(
                      onPressed:
                          _busy ? null : () => _signIn(authService.signInWithApple),
                      style: FilledButton.styleFrom(
                        backgroundColor: p.text,
                        foregroundColor: p.bg,
                      ),
                      child: const Text('Continue with Apple'),
                    ),
                    const SizedBox(height: 12),
                  ],
                  OutlinedButton(
                    onPressed:
                        _busy ? null : () => _signIn(authService.signInWithGoogle),
                    child: const Text('Continue with Google'),
                  ),
                  CupertinoButton(
                    // TODO: connexion e-mail. En bêta : test sans compte.
                    onPressed: _busy ? null : (_testMode ? _testLogin : null),
                    child: Text(_testMode ? 'Test without an account' : 'Use email instead',
                        style: TextStyle(color: p.accent, fontSize: 17)),
                  ),
                ],
              ),
            ),
          ),
        ],
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
          borderRadius: BorderRadius.circular(14),
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
                    Text('Detected from your phone',
                        style: TextStyle(fontSize: 13, color: p.text2)),
                ],
              ),
            ),
            CupertinoButton(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              minSize: 34,
              color: p.accent.withValues(alpha: .12),
              borderRadius: BorderRadius.circular(17),
              onPressed: () => _showLanguageSheet(context),
              child: Text('Change',
                  style: TextStyle(
                      color: p.accent,
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
            header: const Text('THE LANGUAGE YOUR TUTOR EXPLAINS IN'),
            footer: const Text('More languages are coming.'),
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
