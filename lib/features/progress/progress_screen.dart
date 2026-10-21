import 'dart:math' as math;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/learning/learner_store.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

/// Écran 5 : progression dans le programme A1 (unité par unité) et compétences.
class ProgressScreen extends StatefulWidget {
  const ProgressScreen({super.key});

  @override
  State<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends State<ProgressScreen> {
  /// Avancement par unité, calculé par le serveur (mots déjà présentés).
  late final Future<Map<String, dynamic>?> _progress = _load();

  Future<Map<String, dynamic>?> _load() async {
    try {
      final r = await api.get('/me/progress');
      final total = (r['words_learned'] as num?)?.toInt();
      if (total != null) learnerStore.setLearnedTotal(total);
      return r;
    } catch (_) {
      return null; // hors ligne : on affiche ce que l'appareil sait
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return FutureBuilder<Map<String, dynamic>?>(
      future: _progress,
      builder: (context, snap) => ValueListenableBuilder(
      valueListenable: learnerStore,
      builder: (context, s, _) {
        final prog = snap.data;
        final units = ((prog?['units'] as List?) ?? const []).cast<Map<String, dynamic>>();
        final current = (prog?['current_unit'] as num?)?.toInt();
        final level = (prog?['a1_progress'] as num?)?.toDouble() ?? s.levelProgress;
        final pct = (level * 100).round();
        return Stack(
          children: [
            CustomScrollView(
              slivers: [
                largeTitleBar(context, 'Progression'),
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                  sliver: SliverList.list(children: [
                    AppCard(
                      padding: const EdgeInsets.all(18),
                      child: Row(children: [
                        Semantics(
                          label: 'Niveau A1, $pct pour cent',
                          child: SizedBox(
                            width: 88,
                            height: 88,
                            child: CustomPaint(
                              painter: _RingPainter(level, p.fill, p.accent),
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
                              Text('Le début · $pct %', style: TextStyle(fontSize: 15, color: p.text2)),
                              const SizedBox(height: 8),
                              Wrap(spacing: 16, children: [
                                _Stat((prog?['words_seen'] as num?)?.toInt() ?? 0, 'mots vus'),
                                _Stat(s.learnedTotal, s.learnedTotal > 1 ? 'réemployés' : 'réemployé'),
                              ]),
                            ],
                          ),
                        ),
                      ]),
                    ),
                    const SizedBox(height: 8),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
                      child: Text('TON PARCOURS A1', style: TextStyle(fontSize: 13, color: p.text2)),
                    ),
                    if (units.isEmpty)
                      AppCard(
                        child: snap.connectionState == ConnectionState.waiting
                            ? const Center(child: Spinner())
                            : Text('Ton parcours s’affichera ici dès que tu seras en ligne.',
                                style: TextStyle(fontSize: 15, color: p.text2)),
                      )
                    else
                      AppCard(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                        child: Column(children: [
                          for (final (i, u) in units.indexed)
                            _UnitRow(
                              index: i + 1,
                              title: u['title'] as String,
                              subtitle: (u['subtitle'] as String?) ?? '',
                              seen: (u['seen'] as num).toInt(),
                              total: (u['total'] as num).toInt(),
                              current: i == current,
                              last: i == units.length - 1,
                            ),
                        ]),
                      ),
                    const SizedBox(height: 8),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 8, 16, 6),
                      child: Text('COMPÉTENCES', style: TextStyle(fontSize: 13, color: p.text2)),
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
                                  child: Text(_skillLabels[e.key] ?? e.key, style: TextStyle(fontSize: 15, color: p.text))),
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
      ),
    );
  }
}

/// Une unité du programme : numéro, titre, mots vus / total, barre d'avancement.
class _UnitRow extends StatelessWidget {
  const _UnitRow({
    required this.index,
    required this.title,
    required this.subtitle,
    required this.seen,
    required this.total,
    required this.current,
    required this.last,
  });
  final int index, seen, total;
  final String title, subtitle;
  final bool current, last;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final done = total > 0 && seen >= total;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(
        border: last ? null : Border(bottom: BorderSide(color: p.separator, width: .5)),
      ),
      child: Row(children: [
        Container(
          width: 32,
          height: 32,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: done ? p.accent : (current ? p.ink : p.fill),
            borderRadius: BorderRadius.circular(9),
          ),
          child: done
              ? Icon(CupertinoIcons.check_mark, size: 16, color: p.onAccent)
              : Text('$index',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: current ? p.onInk : p.text2)),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(
                child: Text(title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 16, fontWeight: current ? FontWeight.w600 : FontWeight.w400, color: p.text)),
              ),
              Text(current ? 'En cours · $seen/$total' : '$seen/$total',
                  style: TextStyle(fontSize: 13, color: current ? p.accentText : p.text2)),
            ]),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: total == 0 ? 0 : seen / total,
                minHeight: 5,
                backgroundColor: p.fill,
                color: p.accent,
              ),
            ),
          ]),
        ),
      ]),
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

const _skillLabels = {
  'Vocabulary': 'Vocabulaire',
  'Understanding': 'Compréhension',
  'Grammar': 'Grammaire',
  'Culture': 'Culture',
};
