import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../content/sample_content.dart';
import '../theme/app_theme.dart';
import '../theme/filigree.dart';
import 'common.dart';

/// Carte « mot » : le mot kabyle, son écriture tifinagh et son sens.
class WordCard extends StatelessWidget {
  const WordCard(
      {super.key, required this.word, this.caption = 'Word of the day', this.compact = false, this.color});
  final WordOfTheDay word;
  final String caption;
  final bool compact;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return AppCard(
      color: color,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Caption(caption),
          const SizedBox(height: 8),
          Text(word.word, style: AppTheme.serif(size: compact ? 24 : 28, color: p.text)),
          if (word.tifinagh.isNotEmpty)
            ExcludeSemantics(
              child: Text(word.tifinagh,
                  style: AppTheme.tifinagh(size: 13, color: p.text2).copyWith(letterSpacing: 2)),
            ),
          const SizedBox(height: 4),
          Text(word.meaning,
              maxLines: compact ? null : 3,
              overflow: compact ? null : TextOverflow.ellipsis,
              style: TextStyle(fontSize: 15, color: p.text2)),
        ],
      ),
    );
  }
}

/// Petite carte de capsule culturelle ; un tap ouvre le texte complet.
class CapsuleCard extends StatelessWidget {
  const CapsuleCard({super.key, required this.capsule, this.showBody = false});
  final CultureCapsule capsule;
  final bool showBody;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return GestureDetector(
      onTap: () => showCapsuleSheet(context, capsule),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(22),
        child: Stack(children: [
          AppCard(
            color: p.goldSoft,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Caption('Culture · ${capsule.title}', color: p.gold),
                const SizedBox(height: 8),
                Text(capsule.kab.isNotEmpty ? capsule.kab : capsule.title,
                    style: AppTheme.serif(size: 19, color: p.text).copyWith(height: 1.25)),
                if (showBody) ...[
                  const SizedBox(height: 6),
                  Text(capsule.body,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 14, height: 1.4, color: p.text2)),
                ],
                const SizedBox(height: 6),
                Text('Read', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: p.gold)),
              ],
            ),
          ),
          Positioned(right: -40, top: -40, child: Rosette(size: 110, opacity: .22, color: p.gold)),
        ]),
      ),
    );
  }
}

/// Feuille iOS avec le texte complet d'une capsule.
Future<void> showCapsuleSheet(BuildContext context, CultureCapsule c) {
  return showModalBottomSheet(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) {
      final p = AppPalette.of(context);
      return DraggableScrollableSheet(
        initialChildSize: .6,
        maxChildSize: .92,
        minChildSize: .3,
        expand: false,
        builder: (context, scroll) => Container(
          decoration: BoxDecoration(
            color: p.bg,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: ListView(
            controller: scroll,
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 32),
            children: [
              Center(
                child: Container(
                  width: 36,
                  height: 5,
                  decoration: BoxDecoration(color: p.separator, borderRadius: BorderRadius.circular(3)),
                ),
              ),
              const SizedBox(height: 18),
              Caption('Culture · ${c.title}', color: p.gold),
              const SizedBox(height: 8),
              Text(c.kab.isNotEmpty ? c.kab : c.title, style: AppTheme.serif(size: 28, color: p.text)),
              const SizedBox(height: 14),
              Text(c.body, style: TextStyle(fontSize: 17, height: 1.55, color: p.text)),
              const SizedBox(height: 24),
              Center(child: Rosette(size: 48, opacity: .5, color: p.gold)),
            ],
          ),
        ),
      );
    },
  );
}

/// Exercice compact à choix, affiché dans le chat.
class InlineExercise extends StatefulWidget {
  const InlineExercise({super.key, required this.exercise, this.onCorrect, this.color});
  final ChoiceExercise exercise;
  final VoidCallback? onCorrect;
  final Color? color;

  @override
  State<InlineExercise> createState() => _InlineExerciseState();
}

class _InlineExerciseState extends State<InlineExercise> {
  String? _picked;
  bool get _done => _picked == widget.exercise.answer;

  void _pick(String o) {
    if (_done) return;
    setState(() => _picked = o);
    if (o == widget.exercise.answer) widget.onCorrect?.call();
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final ex = widget.exercise;
    return AppCard(
      radius: 18,
      color: widget.color,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Caption(ex.instruction),
          const SizedBox(height: 6),
          Text(ex.hasBlank ? '${ex.before}_____${ex.after}' : ex.before,
              style: AppTheme.serif(size: 24, color: p.text)),
          if (ex.tifinagh != null && ex.tifinagh!.isNotEmpty)
            ExcludeSemantics(
              child: Text(ex.tifinagh!,
                  style: AppTheme.tifinagh(size: 13, color: p.text2).copyWith(letterSpacing: 2)),
            ),
          const SizedBox(height: 12),
          for (final o in ex.options) ...[
            GestureDetector(
              onTap: () => _pick(o),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                decoration: BoxDecoration(
                  color: _picked == o ? (o == ex.answer ? p.greenSoft : p.goldSoft) : (widget.color != null ? p.surface : p.fill),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(o,
                    style: TextStyle(
                      fontSize: 15,
                      color: _picked == o ? (o == ex.answer ? p.green : p.gold) : p.text,
                      fontWeight: _picked == o ? FontWeight.w600 : FontWeight.w400,
                    )),
              ),
            ),
            const SizedBox(height: 8),
          ],
          if (_picked != null)
            Text(
              _done ? ex.explanation : 'Not quite — try another one.',
              style: TextStyle(fontSize: 14, height: 1.4, color: _done ? p.green : p.gold),
            ),
        ],
      ),
    );
  }
}
