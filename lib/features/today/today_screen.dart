import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../content/sample_content.dart';
import '../../core/learning/learner_store.dart';
import '../../core/locale/locale_controller.dart';
import '../../theme/app_theme.dart';
import '../../theme/filigree.dart';
import '../../widgets/common.dart';
import '../exercise/exercise_screen.dart';

/// Écran 3 : la séance du jour, adaptée au temps écoulé, sans culpabiliser.
class TodayScreen extends StatelessWidget {
  const TodayScreen({super.key, required this.onOpenTutor});

  final VoidCallback onOpenTutor;

  void _start(BuildContext context) {
    Navigator.of(context, rootNavigator: true).push(
      CupertinoPageRoute(fullscreenDialog: true, builder: (_) => const ExerciseScreen(lesson: firstWords)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return ValueListenableBuilder(
      valueListenable: learnerStore,
      builder: (context, s, _) {
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
              slivers: [
                largeTitleBar(
                  context,
                  s.name.isEmpty ? 'Azul' : 'Azul, ${s.name}',
                ),
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
                          Text(firstWords.title, style: AppTheme.serif(size: 26, color: p.text)),
                          const SizedBox(height: 4),
                          Text(welcome, style: TextStyle(fontSize: 15, color: p.text2)),
                          const SizedBox(height: 14),
                          if (s.dueCount > 0)
                            _Step(CupertinoIcons.arrow_2_circlepath,
                                'Review ${s.dueCount} words before they fade'),
                          _Step(CupertinoIcons.sparkles, 'New: ${firstWords.subtitle.toLowerCase()}'),
                          _Step(CupertinoIcons.chat_bubble_fill, 'Short chat with your tutor',
                              onTap: onOpenTutor),
                          const SizedBox(height: 14),
                          PrimaryButton(label: 'Start session', onPressed: () => _start(context)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    IntrinsicHeight(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(
                            child: AppCard(
                              child: Stack(children: [
                                Positioned(
                                  right: 0,
                                  top: 0,
                                  child: ExcludeSemantics(
                                    child: Text(wordOfTheDay.tifinagh,
                                        style: AppTheme.tifinagh(size: 13, color: p.text2)
                                            .copyWith(letterSpacing: 2)),
                                  ),
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Caption('Word of the day'),
                                    const SizedBox(height: 8),
                                    Text(wordOfTheDay.word, style: AppTheme.serif(size: 28, color: p.text)),
                                    Text(wordOfTheDay.meaning, style: TextStyle(fontSize: 15, color: p.text2)),
                                  ],
                                ),
                              ]),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: AppCard(
                              color: p.goldSoft,
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Caption('Culture · 2 min', color: p.gold),
                                  const SizedBox(height: 8),
                                  Text('Who was Mouloud Mammeri?',
                                      style: AppTheme.serif(size: 19, color: p.text).copyWith(height: 1.25)),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    AppCard(
                      radius: 16,
                      child: Row(children: [
                        Text('${s.wordsRemembered}',
                            style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: p.green)),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'words remembered. Come back whenever you like — reviews adapt to you.',
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
