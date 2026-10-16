import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../content/sample_content.dart';
import '../../core/api/api_client.dart';
import '../../core/learning/learner_store.dart';
import '../../theme/app_theme.dart';
import '../../theme/mark.dart';
import '../../widgets/common.dart';

/// Écran 4 : une séance d'exercices, une question à la fois, retour
/// immédiat et bienveillant, capsule culturelle à la fin.
class ExerciseScreen extends StatefulWidget {
  const ExerciseScreen({super.key, required this.lesson});
  final Lesson lesson;

  @override
  State<ExerciseScreen> createState() => _ExerciseScreenState();
}

class _ExerciseScreenState extends State<ExerciseScreen> {
  int _index = 0;
  String? _picked;
  bool _missedOnce = false;
  late bool _showCapsule = widget.lesson.exercises.isEmpty && widget.lesson.capsule != null;

  List<ChoiceExercise> get _items => widget.lesson.exercises;
  ChoiceExercise get _ex => _items[_index];
  bool get _correct => _picked == _ex.answer;

  void _pick(String option) {
    if (_picked != null && _correct) return;
    setState(() => _picked = option);
    final correct = option == _ex.answer;
    if (correct) {
      // Le mot est « découvert » aujourd'hui ; il comptera comme appris quand
      // l'élève l'emploiera dans une conversation un autre jour.
      api.post('/learning/seen', {
        'words': [_ex.hasBlank ? _ex.answer : _ex.before],
      }).catchError((_) => <String, dynamic>{});
      learnerStore.recordAnswer(
        id: _ex.id,
        kabyle: _ex.hasBlank ? _ex.answer : _ex.before,
        translation: _ex.hasBlank ? (_ex.translation ?? '') : _ex.answer,
        correct: true,
        firstTry: !_missedOnce,
        skill: _ex.hasBlank ? 'Grammar' : 'Vocabulary',
      );
    } else {
      _missedOnce = true;
    }
  }

  void _next() {
    if (_index < _items.length - 1) {
      setState(() {
        _index++;
        _picked = null;
        _missedOnce = false;
      });
    } else if (widget.lesson.capsule != null && !_showCapsule) {
      setState(() => _showCapsule = true);
    } else {
      learnerStore.finishSession(withCapsule: widget.lesson.capsule != null);
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    if (_items.isEmpty && !_showCapsule) {
      return Scaffold(
        body: SafeArea(
          child: Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text('Cette leçon arrive bientôt.', style: TextStyle(fontSize: 17, color: p.text2)),
              const SizedBox(height: 16),
              CupertinoButton(child: const Text('Fermer'), onPressed: () => Navigator.of(context).pop(false)),
            ]),
          ),
        ),
      );
    }
    final progress = _showCapsule || _items.isEmpty ? 1.0 : (_index + (_correct ? 1 : 0)) / _items.length;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(children: [
                Semantics(
                  label: 'Fermer',
                  button: true,
                  child: CupertinoButton(
                    padding: EdgeInsets.zero,
                    minSize: 32,
                    onPressed: () => Navigator.of(context).pop(false),
                    child: Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(color: p.fill, shape: BoxShape.circle),
                      child: Icon(CupertinoIcons.xmark, size: 14, color: p.text2),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(3),
                    child: LinearProgressIndicator(
                      value: progress,
                      minHeight: 6,
                      backgroundColor: p.fill,
                      color: p.accent,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Text('${_showCapsule ? _items.length : _index + 1} sur ${_items.length}',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: p.text2)),
              ]),
              const SizedBox(height: 28),
              Expanded(child: _showCapsule ? _capsule(p) : _question(p)),
              PrimaryButton(
                label: _showCapsule ? 'Terminer' : 'Continuer',
                onPressed: _showCapsule || _correct ? _next : null,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _question(AppPalette p) {
    final ex = _ex;
    final answered = _picked != null;
    return ListView(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Caption(ex.instruction),
              const SizedBox(height: 10),
              if (ex.hasBlank)
                Text.rich(
                  TextSpan(children: [
                    TextSpan(text: ex.before),
                    TextSpan(
                      text: _correct ? ex.answer : '_____',
                      style: TextStyle(
                        color: _correct ? p.green : p.text2,
                        decoration: TextDecoration.underline,
                        decorationColor: _correct ? p.green : p.separator,
                      ),
                    ),
                    TextSpan(text: ex.after),
                  ]),
                  style: AppTheme.serif(size: 34, color: p.text).copyWith(height: 1.3),
                )
              else
                Text(ex.before, style: AppTheme.serif(size: 40, color: p.text)),
              if (ex.tifinagh != null && ex.tifinagh!.isNotEmpty) ...[
                const SizedBox(height: 4),
                ExcludeSemantics(
                  child: Text(ex.tifinagh!,
                      style: AppTheme.tifinagh(size: 16, color: p.text2).copyWith(letterSpacing: 2)),
                ),
              ],
              if (ex.translation != null) ...[
                const SizedBox(height: 8),
                Text(ex.translation!, style: TextStyle(fontSize: 17, color: p.text2)),
              ],
            ],
          ),
        ),
        const SizedBox(height: 24),
        // Options courtes : côte à côte ; longues (définitions) : empilées.
        if (ex.options.every((o) => o.length <= 12))
          Row(
            children: [
              for (final o in ex.options) ...[
                Expanded(child: _option(ex, o, answered)),
                if (o != ex.options.last) const SizedBox(width: 10),
              ],
            ],
          )
        else
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final o in ex.options) ...[
                _option(ex, o, answered),
                if (o != ex.options.last) const SizedBox(height: 10),
              ],
            ],
          ),
        const SizedBox(height: 20),
        if (answered)
          AppCard(
            radius: 18,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Icon(_correct ? CupertinoIcons.checkmark_circle_fill : CupertinoIcons.arrow_counterclockwise_circle_fill,
                      color: _correct ? p.green : p.gold, size: 22),
                  const SizedBox(width: 8),
                  Text(_correct ? 'C’est ça.' : 'Pas tout à fait — essaie une autre réponse.',
                      style: TextStyle(
                          fontSize: 17, fontWeight: FontWeight.w600, color: _correct ? p.green : p.gold)),
                ]),
                if (_correct) ...[
                  const SizedBox(height: 8),
                  Text(ex.explanation, style: TextStyle(fontSize: 15, height: 1.5, color: p.text)),
                ],
              ],
            ),
          ),
      ],
    );
  }

  Widget _option(ChoiceExercise ex, String o, bool answered) => _OptionButton(
        label: o,
        state: _picked != o
            ? _OptionState.idle
            : (o == ex.answer ? _OptionState.right : _OptionState.wrong),
        dimmed: answered && _correct && o != ex.answer,
        onTap: () => _pick(o),
      );

  Widget _capsule(AppPalette p) {
    final c = widget.lesson.capsule!;
    return ListView(
      children: [
        const SizedBox(height: 24),
        ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: Stack(
            children: [
              AppCard(
                color: p.goldSoft,
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Caption('Culture · ${c.title}', color: p.gold),
                    const SizedBox(height: 6),
                    Text(c.kab.isNotEmpty ? c.kab : c.title, style: AppTheme.serif(size: 26, color: p.text)),
                    const SizedBox(height: 8),
                    Text(c.body, style: TextStyle(fontSize: 16, height: 1.5, color: p.text)),
                  ],
                ),
              ),
              Positioned(right: 18, top: 18, child: AmusnawMark(size: 26, color: p.gold)),
            ],
          ),
        ),
        const SizedBox(height: 24),
        Text('Leçon terminée. Tanemmirt !',
            style: TextStyle(fontSize: 17, color: p.text2)),
      ],
    );
  }
}

enum _OptionState { idle, right, wrong }

class _OptionButton extends StatelessWidget {
  const _OptionButton({required this.label, required this.state, required this.onTap, this.dimmed = false});
  final String label;
  final _OptionState state;
  final bool dimmed;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final (bg, border, fg) = switch (state) {
      _OptionState.right => (p.greenSoft, p.green, p.green),
      _OptionState.wrong => (p.goldSoft, p.gold, p.gold),
      _OptionState.idle => (p.surface, Colors.transparent, dimmed ? p.text2 : p.text),
    };
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        constraints: const BoxConstraints(minHeight: 52),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: border, width: 2),
        ),
        child: Semantics(
          button: true,
          child: Text(label,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 17, color: fg, fontWeight: state == _OptionState.idle ? FontWeight.w400 : FontWeight.w600)),
        ),
      ),
    );
  }
}
