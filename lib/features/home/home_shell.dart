import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_service.dart';
import '../../core/auth/session.dart';
import '../../core/learning/learner_store.dart';
import '../../theme/app_theme.dart';
import '../learn/learn_screen.dart';
import '../progress/progress_screen.dart';
import '../today/today_screen.dart';
import '../tutor/tutor_chat_screen.dart';

/// Barre d'onglets iOS : Today · Tutor · Learn · Progress.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _controller = CupertinoTabController();

  @override
  void initState() {
    super.initState();
    _syncProgress();
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

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Material(
      color: p.bg,
      child: CupertinoTabScaffold(
        controller: _controller,
        backgroundColor: p.bg,
        tabBar: CupertinoTabBar(
          activeColor: p.accent,
          inactiveColor: p.text2,
          backgroundColor: p.surface.withValues(alpha: .94),
          border: Border(top: BorderSide(color: p.separator, width: .5)),
          items: const [
            BottomNavigationBarItem(
                icon: Icon(CupertinoIcons.house), activeIcon: Icon(CupertinoIcons.house_fill), label: 'Today'),
            BottomNavigationBarItem(
                icon: Icon(CupertinoIcons.chat_bubble),
                activeIcon: Icon(CupertinoIcons.chat_bubble_fill),
                label: 'Tutor'),
            BottomNavigationBarItem(
                icon: Icon(CupertinoIcons.book), activeIcon: Icon(CupertinoIcons.book_fill), label: 'Learn'),
            BottomNavigationBarItem(
                icon: Icon(CupertinoIcons.chart_bar),
                activeIcon: Icon(CupertinoIcons.chart_bar_fill),
                label: 'Progress'),
          ],
        ),
        tabBuilder: (context, i) => CupertinoTabView(
          builder: (_) => Material(
            color: p.bg,
            child: switch (i) {
              0 => TodayScreen(onOpenTutor: () => _controller.index = 1),
              1 => const TutorChatScreen(),
              2 => const LearnScreen(),
              _ => const ProgressScreen(),
            },
          ),
        ),
      ),
    );
  }
}
