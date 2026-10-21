import 'package:flutter/material.dart';

import '../../content/sample_content.dart';
import '../../core/content/content_repository.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';
import '../../widgets/dialogs.dart';
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
      await Navigator.of(context, rootNavigator: true).push(appRoute((_) => ExerciseScreen(lesson: lesson)));
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
        return RefreshIndicator(
          onRefresh: _refresh,
          color: p.accent,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              largeTitleBar(context, 'Leçons'),
              if (all == null)
                const SliverToBoxAdapter(
                  child: Padding(padding: EdgeInsets.all(32), child: Center(child: Spinner())),
                ),
              for (final entry in levels.entries)
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 6, 16, 22),
                  sliver: SliverList.list(children: [
                    Padding(padding: const EdgeInsets.fromLTRB(6, 0, 6, 8), child: Caption(entry.key)),
                    AppCard(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Column(children: [
                        for (var i = 0; i < entry.value.length; i++) ...[
                          if (i > 0) Divider(height: 1, thickness: .5, indent: 58, color: p.separator),
                          _LessonRow(
                            lesson: entry.value[i],
                            busy: _opening == entry.value[i].id,
                            onTap: entry.value[i].count == 0 ? null : () => _open(entry.value[i]),
                          ),
                        ],
                      ]),
                    ),
                    if (entry.key == levels.keys.last)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(6, 8, 6, 0),
                        child: Text('De nouvelles leçons arrivent régulièrement.',
                            style: TextStyle(fontSize: 13, color: p.text2)),
                      ),
                  ]),
                ),
            ],
          ),
        );
      },
    );
  }
}

class _LessonRow extends StatelessWidget {
  const _LessonRow({required this.lesson, required this.busy, this.onTap});
  final LessonSummary lesson;
  final bool busy;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final locked = lesson.count == 0;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(children: [
          Container(
            width: 32,
            height: 32,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: p.accentSoft, borderRadius: BorderRadius.circular(10)),
            child: Icon(locked ? Icons.lock_outline_rounded : Icons.menu_book_rounded, size: 18, color: p.accentText),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(lesson.title, style: TextStyle(fontSize: 16, color: locked ? p.text2 : p.text)),
              const SizedBox(height: 2),
              Text(locked ? lesson.subtitle : '${lesson.subtitle} · ${lesson.count} questions',
                  style: TextStyle(fontSize: 13.5, color: p.text2)),
            ]),
          ),
          if (busy)
            const Spinner(size: 18)
          else if (!locked)
            Icon(Icons.chevron_right_rounded, size: 22, color: p.text2),
        ]),
      ),
    );
  }
}
