import 'package:flutter/cupertino.dart';

import '../../content/sample_content.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';
import '../exercise/exercise_screen.dart';

/// Onglet Learn : leçons du niveau en cours.
class LearnScreen extends StatelessWidget {
  const LearnScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return CustomScrollView(
      slivers: [
        largeTitleBar(context, 'Learn'),
        SliverToBoxAdapter(
          child: CupertinoListSection.insetGrouped(
            backgroundColor: p.bg,
            header: const Text('A1 · FIRST WORDS'),
            footer: const Text('New lessons unlock as you progress.'),
            children: [
              for (final l in a1Lessons)
                CupertinoListTile(
                  leading: TintIcon(l.exercises.isEmpty ? CupertinoIcons.lock_fill : CupertinoIcons.book_fill),
                  title: Text(l.title, style: TextStyle(color: l.exercises.isEmpty ? p.text2 : p.text)),
                  subtitle: Text(l.subtitle, style: TextStyle(color: p.text2)),
                  trailing: l.exercises.isEmpty ? null : const CupertinoListTileChevron(),
                  onTap: l.exercises.isEmpty
                      ? null
                      : () => Navigator.of(context, rootNavigator: true).push(CupertinoPageRoute(
                            fullscreenDialog: true,
                            builder: (_) => ExerciseScreen(lesson: l),
                          )),
                ),
            ],
          ),
        ),
      ],
    );
  }
}
