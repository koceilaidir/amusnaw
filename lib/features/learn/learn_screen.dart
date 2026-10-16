import 'package:flutter/cupertino.dart';

import '../../content/sample_content.dart';
import '../../core/content/content_repository.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';
import '../exercise/exercise_screen.dart';

/// Onglet Learn : leçons servies par le serveur, groupées par niveau.
class LearnScreen extends StatefulWidget {
  const LearnScreen({super.key});

  @override
  State<LearnScreen> createState() => _LearnScreenState();
}

class _LearnScreenState extends State<LearnScreen> {
  late Future<List<LessonSummary>> _lessons = contentRepository.lessons();
  String? _opening;

  Future<void> _refresh() async {
    final f = contentRepository.lessons(refresh: true);
    setState(() => _lessons = f);
    await f;
  }

  Future<void> _open(LessonSummary s) async {
    if (_opening != null) return;
    setState(() => _opening = s.id);
    try {
      final lesson = await contentRepository.lesson(s.id);
      if (!mounted) return;
      await Navigator.of(context, rootNavigator: true).push(CupertinoPageRoute(
        fullscreenDialog: true,
        builder: (_) => ExerciseScreen(lesson: lesson),
      ));
    } finally {
      if (mounted) setState(() => _opening = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return FutureBuilder<List<LessonSummary>>(
      future: _lessons,
      builder: (context, snap) {
        final all = snap.data;
        final levels = <String, List<LessonSummary>>{};
        for (final l in all ?? const <LessonSummary>[]) {
          levels.putIfAbsent(l.level, () => []).add(l);
        }
        return CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            largeTitleBar(context, 'Leçons'),
            CupertinoSliverRefreshControl(onRefresh: _refresh),
            if (all == null)
              const SliverToBoxAdapter(
                child: Padding(padding: EdgeInsets.all(32), child: CupertinoActivityIndicator()),
              ),
            for (final entry in levels.entries)
              SliverToBoxAdapter(
                child: CupertinoListSection.insetGrouped(
                  backgroundColor: p.bg,
                  header: Text(entry.key.toUpperCase()),
                  footer: entry.key == levels.keys.last
                      ? const Text('De nouvelles leçons arrivent régulièrement.')
                      : null,
                  children: [
                    for (final l in entry.value)
                      CupertinoListTile(
                        leading: TintIcon(l.count == 0 ? CupertinoIcons.lock_fill : CupertinoIcons.book_fill),
                        title: Text(l.title, style: TextStyle(color: l.count == 0 ? p.text2 : p.text)),
                        subtitle: Text(
                          l.count == 0 ? l.subtitle : '${l.subtitle} · ${l.count} questions',
                          style: TextStyle(color: p.text2),
                        ),
                        trailing: _opening == l.id
                            ? const CupertinoActivityIndicator()
                            : (l.count == 0 ? null : const CupertinoListTileChevron()),
                        onTap: l.count == 0 ? null : () => _open(l),
                      ),
                  ],
                ),
              ),
          ],
        );
      },
    );
  }
}
