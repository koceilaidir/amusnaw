import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../content/sample_content.dart';
import '../../core/content/content_repository.dart';
import '../../core/learning/learner_store.dart';
import '../../core/learning/spaced_repetition.dart';
import '../../core/locale/locale_controller.dart';
import '../../theme/app_theme.dart';
import '../../theme/filigree.dart';
import '../../widgets/common.dart';
import '../../widgets/content_cards.dart';
import '../exercise/exercise_screen.dart';
import '../settings/settings_screen.dart';

/// Écran 3 : la séance du jour, adaptée au temps écoulé, sans culpabiliser.
/// Le mot du jour, la capsule et la leçon viennent du serveur.
class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key, required this.onOpenTutor});

  final VoidCallback onOpenTutor;

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  late Future<TodayContent> _today = contentRepository.today();
  bool _starting = false;

  Future<void> _refresh() async {
    final f = contentRepository.today(refresh: true);
    setState(() => _today = f);
    await f;
  }

  /// Révisions (cartes à revoir) d'abord, puis la leçon du jour.
  Future<void> _start(TodayContent t) async {
    if (_starting) return;
    setState(() => _starting = true);
    try {
      final base = await contentRepository.lesson(t.lessonId ?? firstWords.id);
      final review = _reviewExercises(learnerStore.value.cards.values.toList());
      final lesson = Lesson(
        id: base.id,
        title: base.title,
        subtitle: base.subtitle,
        capsule: base.capsule ?? t.capsule,
        exercises: [...review, ...base.exercises.where((e) => !review.any((r) => r.id == e.id))],
      );
      if (!mounted) return;
      await Navigator.of(context, rootNavigator: true).push(
        CupertinoPageRoute(fullscreenDialog: true, builder: (_) => ExerciseScreen(lesson: lesson)),
      );
    } finally {
      if (mounted) setState(() => _starting = false);
    }
  }

  /// Transforme les cartes à revoir (SM-2) en questions « que veut dire… ? ».
  List<ChoiceExercise> _reviewExercises(List<MemoryCard> cards) {
    final due = SpacedRepetition.dueToday(cards, max: 4);
    final meanings = {for (final c in cards) c.translation}..removeWhere((m) => m.isEmpty);
    if (meanings.length < 3) return const [];
    final out = <ChoiceExercise>[];
    for (final c in due) {
      if (c.translation.isEmpty) continue;
      final others = (meanings.toList()..remove(c.translation)..shuffle()).take(2);
      final options = [c.translation, ...others]..shuffle();
      out.add(ChoiceExercise(
        id: c.id,
        instruction: 'REVIEW',
        before: c.kabyle,
        options: options,
        answer: c.translation,
        explanation: '${c.kabyle} — ${c.translation}.',
      ));
    }
    return out;
  }

  void _openSettings() {
    Navigator.of(context, rootNavigator: true).push(
      CupertinoPageRoute(builder: (_) => const SettingsScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return ValueListenableBuilder(
      valueListenable: learnerStore,
      builder: (context, s, _) => FutureBuilder<TodayContent>(
        future: _today,
        builder: (context, snap) {
          final t = snap.data;
          final now = DateTime.now();
          final away = s.daysAway(now);
          final welcome = s.lastSessionAt == null
              ? 'Your first session — just a few minutes.'
              : away >= 2
                  ? 'Welcome back — we’ll start gently.'
                  : 'Picking up where you left off.';
          final date = DateFormat('EEEE d MMMM', localeController.value.code).format(now).toUpperCase();

          return Stack(
            children: [
              const Positioned(top: -110, right: -130, child: Rosette(size: 340, opacity: .12)),
              CustomScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                slivers: [
                  largeTitleBar(
                    context,
                    s.name.isEmpty ? 'Azul' : 'Azul, ${s.name}',
                    trailing: Semantics(
                      label: 'Settings',
                      button: true,
                      child: CupertinoButton(
                        padding: EdgeInsets.zero,
                        minSize: 32,
                        onPressed: _openSettings,
                        child: Icon(CupertinoIcons.person_crop_circle, size: 28, color: p.accent),
                      ),
                    ),
                  ),
                  CupertinoSliverRefreshControl(onRefresh: _refresh),
                  SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                    sliver: SliverList.list(children: [
                      Padding(
                        padding: const EdgeInsets.only(left: 4, bottom: 12),
                        child: Caption(date),
                      ),
                      AppCard(
                        padding: const EdgeInsets.all(18),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [Caption("Today's session"), Caption('8 min')],
                            ),
                            const SizedBox(height: 10),
                            Text(t?.lessonTitle ?? '…', style: AppTheme.serif(size: 26, color: p.text)),
                            const SizedBox(height: 4),
                            Text(welcome, style: TextStyle(fontSize: 15, color: p.text2)),
                            const SizedBox(height: 14),
                            if (s.dueCount > 0)
                              _Step(CupertinoIcons.arrow_2_circlepath,
                                  'Review ${s.dueCount} words before they fade'),
                            if (t?.lessonSubtitle != null && t!.lessonSubtitle!.isNotEmpty)
                              _Step(CupertinoIcons.sparkles, 'New: ${t.lessonSubtitle!.toLowerCase()}'),
                            _Step(CupertinoIcons.chat_bubble_fill, 'Short chat with your tutor',
                                onTap: widget.onOpenTutor),
                            const SizedBox(height: 14),
                            PrimaryButton(
                              label: _starting ? 'Loading…' : 'Start session',
                              onPressed: t == null || _starting ? null : () => _start(t!),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      if (t != null)
                        IntrinsicHeight(
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              if (t.word != null) Expanded(child: WordCard(word: t.word!)),
                              if (t.word != null && t.capsule != null) const SizedBox(width: 12),
                              if (t.capsule != null) Expanded(child: CapsuleCard(capsule: t.capsule!)),
                            ],
                          ),
                        )
                      else
                        const Padding(
                          padding: EdgeInsets.all(24),
                          child: Center(child: CupertinoActivityIndicator()),
                        ),
                      const SizedBox(height: 12),
                      AppCard(
                        radius: 16,
                        child: Row(children: [
                          Text('${s.learnedTotal}',
                              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: p.green)),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              'words learned. Use them in a chat on another day and the count goes up.',
                              style: TextStyle(fontSize: 14, height: 1.35, color: p.text2),
                            ),
                          ),
                        ]),
                      ),
                    ]),
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Step extends StatelessWidget {
  const _Step(this.icon, this.label, {this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          TintIcon(icon),
          const SizedBox(width: 12),
          Expanded(child: Text(label, style: TextStyle(fontSize: 15, color: p.text))),
        ]),
      ),
    );
  }
}
