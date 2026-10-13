import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

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
