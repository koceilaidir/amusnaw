import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../core/auth/auth_service.dart';
import '../../core/auth/google_button.dart';
import '../../core/chat/conversation_store.dart';
import '../../core/learning/learner_store.dart';
import '../../theme/app_theme.dart';
import '../../theme/mark.dart';

/// « Garde ta progression » : proposé au visiteur sans compte après quelques
/// messages, et depuis le menu. Sa progression et ses discussions passent
/// sur le compte créé. Renvoie vrai si un compte a été créé ou ouvert.
Future<bool> showAccountDialog(BuildContext context) async {
  if (!authService.googleEnabled) return false; // pas encore configuré sur ce serveur
  final ok = await showDialog<bool>(
    context: context,
    useRootNavigator: true,
    barrierColor: const Color(0x73000000),
    builder: (_) => const _AccountDialog(),
  );
  return ok == true;
}

class _AccountDialog extends StatefulWidget {
  const _AccountDialog();

  @override
  State<_AccountDialog> createState() => _AccountDialogState();
}

class _AccountDialogState extends State<_AccountDialog> {
  StreamSubscription<AuthSession>? _sub;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (kIsWeb) {
      authService.initGoogleWeb();
      _sub = authService.webGoogleSessions.listen(_done, onError: (_) => _fail());
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  Future<void> _done(AuthSession s) async {
    learnerStore.setName(s.name);
    await conversationStore.syncWithServer(); // les discussions du compte reviennent
    if (mounted) Navigator.of(context).pop(true);
  }

  void _fail() {
    if (mounted) setState(() => _error = 'La connexion a échoué. Réessaie dans un instant.');
  }

  Future<void> _mobileGoogle() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final s = await authService.signInWithGoogle();
      if (s != null) await _done(s);
    } catch (_) {
      _fail();
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Dialog(
      backgroundColor: p.surface,
      insetPadding: const EdgeInsets.all(24),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(26, 26, 26, 14),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Align(
              alignment: Alignment.centerLeft,
              child: Container(
                width: 52,
                height: 52,
                alignment: Alignment.center,
                decoration: BoxDecoration(color: const Color(0xFF56662E), borderRadius: BorderRadius.circular(14)),
                child: const AmusnawMark(size: 36, color: Color(0xFFF8F6F1)),
              ),
            ),
            const SizedBox(height: 18),
            Text('Garde ta progression', style: AppTheme.serif(size: 28, color: p.text)),
            const SizedBox(height: 8),
            Text(
              'Crée ton compte gratuit pour retrouver tes discussions et les mots que tu as appris, '
              'sur ton téléphone comme sur ordinateur. Tout ce que tu as déjà fait est gardé.',
              style: TextStyle(fontSize: 16, height: 1.45, color: p.text2),
            ),
            const SizedBox(height: 22),
            if (_busy)
              const Padding(padding: EdgeInsets.all(14), child: CupertinoActivityIndicator())
            else
              GoogleButton(onPressed: _mobileGoogle),
            if (_error != null) ...[
              const SizedBox(height: 10),
              Text(_error!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14, color: Color(0xFFC0392B))),
            ],
            const SizedBox(height: 6),
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text('Plus tard', style: TextStyle(fontSize: 16, color: p.text2)),
            ),
          ]),
        ),
      ),
    );
  }
}
