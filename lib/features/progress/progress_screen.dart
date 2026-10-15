import 'dart:math' as math;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../core/learning/learner_store.dart';
import '../../theme/app_theme.dart';
import '../../theme/filigree.dart';
import '../../widgets/common.dart';

/// Écran 5 : progression A1 → B2 et compétences.
class ProgressScreen extends StatelessWidget {
  const ProgressScreen({super.key});

  static const _path = [
    ('A1', 'First words', 'Greetings, family, food'),
    ('A2', 'Everyday life', 'The village, the market'),
    ('B1', 'Real conversations', 'Proverbs, songs, opinions'),
    ('B2', 'Literature & history', 'Poetry, Mammeri, Berber Spring'),
  ];

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return ValueListenableBuilder(
      valueListenable: learnerStore,
      builder: (context, s, _) {
        final pct = (s.levelProgress * 100).round();
        return Stack(
          children: [
            const Positioned(top: -110, right: -130, child: Rosette(size: 340, opacity: .12)),
            CustomScrollView(
              slivers: [
                largeTitleBar(context, 'Progress'),
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                  sliver: SliverList.list(children: [
                    AppCard(
                      padding: const EdgeInsets.all(18),
                      child: Row(children: [
                        Semantics(
                          label: 'Level A1, $pct percent complete',
                          child: SizedBox(
                            width: 88,
                            height: 88,
                            child: CustomPaint(
                              painter: _RingPainter(s.levelProgress, p.fill, p.accent),
                              child: Center(
                                child: Text('A1',
                                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: p.text)),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 18),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Tazwara', style: AppTheme.serif(size: 22, color: p.text)),
                              Text('The beginning · $pct%', style: TextStyle(fontSize: 15, color: p.text2)),
                              const SizedBox(height: 8),
                              Wrap(spacing: 16, children: [
                                _Stat(s.learnedTotal, 'words'),
                                _Stat(s.chats, 'chats'),
                                _Stat(s.capsules, 'stories'),
                              ]),
                            ],
                          ),
                        ),
                      ]),
                    ),
                    const SizedBox(height: 8),
                    CupertinoListSection.insetGrouped(
                      margin: EdgeInsets.zero,
                      backgroundColor: p.bg,
                      header: const Text('YOUR PATH'),
                      children: [
                        for (final (i, (code, title, sub)) in _path.indexed)
                          CupertinoListTile(
                            leading: Container(
                              width: 30,
                              height: 30,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: i == 0 ? p.accent : p.fill,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(code,
                                  style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                      color: i == 0 ? p.onAccent : p.text2)),
                            ),
                            title: Text(title, style: TextStyle(color: p.text)),
                            subtitle: Text(sub, style: TextStyle(color: p.text2)),
                            trailing: i == 0
                                ? Text('Now',
                                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: p.accent))
                                : const CupertinoListTileChevron(),
                          ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
                      child: Text('SKILLS', style: TextStyle(fontSize: 13, color: p.text2)),
                    ),
                    AppCard(
                      radius: 12,
                      child: Column(children: [
                        for (final e in s.skills.entries)
                          Padding(
                            padding: const EdgeInsets.symmetric(vertical: 6),
                            child: Row(children: [
                              SizedBox(
                                  width: 116,
                                  child: Text(e.key, style: TextStyle(fontSize: 15, color: p.text))),
                              Expanded(
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(3),
                                  child: LinearProgressIndicator(
                                    value: e.value,
                                    minHeight: 6,
                                    backgroundColor: p.fill,
                                    color: e.key == 'Culture' ? p.gold : p.accent,
                                  ),
                                ),
                              ),
                            ]),
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

class _Stat extends StatelessWidget {
  const _Stat(this.value, this.label);
  final int value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Text.rich(TextSpan(children: [
      TextSpan(text: '$value ', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: p.text)),
      TextSpan(text: label, style: TextStyle(fontSize: 13, color: p.text2)),
    ]));
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.value, this.track, this.color);
  final double value;
  final Color track, color;

  @override
  void paint(Canvas canvas, Size size) {
    const stroke = 9.0;
    final rect = Offset.zero & size;
    final r = rect.deflate(stroke / 2);
    final base = Paint()
      ..color = track
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    final fg = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(r, 0, 2 * math.pi, false, base);
    if (value > 0) canvas.drawArc(r, -math.pi / 2, 2 * math.pi * value, false, fg);
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.value != value || old.color != color || old.track != track;
}
