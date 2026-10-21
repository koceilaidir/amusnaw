import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../content/sample_content.dart';
import '../theme/app_theme.dart';
import '../theme/mark.dart';
import 'common.dart' show isWide;

/// Petite légende en capitales (EXERCICE, NOUVEAU MOT…).
class _Label extends StatelessWidget {
  const _Label(this.text, {this.color});
  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) => Text(text.toUpperCase(),
      style: TextStyle(
          fontSize: 12, fontWeight: FontWeight.w600, letterSpacing: .6, color: color ?? AppPalette.of(context).text2));
}

BoxDecoration cardDecoration(AppPalette p, {Color? color, double radius = 20}) => BoxDecoration(
      color: color ?? p.surface,
      borderRadius: BorderRadius.circular(radius),
      border: color == null ? Border.all(color: p.separator, width: .5) : null,
      boxShadow: color == null ? p.shadow : null,
    );

/// Carte « mot » : tuile tifinagh, mot kabyle et sens.
class WordCard extends StatelessWidget {
  const WordCard({super.key, required this.word, this.caption = 'Nouveau mot', this.badge});
  final WordOfTheDay word;
  final String caption;

  /// Pastille à droite (« +1 · 25 mots »), facultative.
  final String? badge;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 12, 14, 12),
      decoration: cardDecoration(p),
      child: Row(children: [
        Container(
          width: 52,
          height: 52,
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(color: p.accentSoft, borderRadius: BorderRadius.circular(12)),
          child: ExcludeSemantics(
            child: FittedBox(
              child: Text(word.tifinagh.isEmpty ? 'ⵣ' : word.tifinagh,
                  style: AppTheme.tifinagh(size: 15, color: p.accentText).copyWith(letterSpacing: 1)),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _Label(caption),
            const SizedBox(height: 2),
            Text.rich(
              TextSpan(children: [
                TextSpan(text: word.word, style: const TextStyle(fontWeight: FontWeight.w600)),
                TextSpan(text: ' · ${word.meaning}', style: TextStyle(color: p.text2)),
              ]),
              style: TextStyle(fontSize: 18, color: p.text),
            ),
          ]),
        ),
        if (badge != null) ...[
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: p.greenSoft, borderRadius: BorderRadius.circular(12)),
            child: Text(badge!, style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: p.green)),
          ),
        ],
      ]),
    );
  }
}

/// Carte de capsule culturelle ; un tap ouvre le texte complet.
class CapsuleCard extends StatelessWidget {
  const CapsuleCard({super.key, required this.capsule, this.showBody = false});
  final CultureCapsule capsule;
  final bool showBody;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return GestureDetector(
      onTap: () => showCapsuleSheet(context, capsule),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: cardDecoration(p, color: p.goldSoft),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Label('Culture · ${capsule.title}', color: p.gold),
            const SizedBox(height: 6),
            Text(capsule.kab.isNotEmpty ? capsule.kab : capsule.title,
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: p.text, letterSpacing: -.3)),
            if (showBody) ...[
              const SizedBox(height: 6),
              Text(capsule.body,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 14, height: 1.45, color: p.text2)),
            ],
            const SizedBox(height: 8),
            Text('Lire', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: p.gold)),
          ],
        ),
      ),
    );
  }
}

/// Fiche (mot du jour, capsule) : fenêtre centrée sur ordinateur, feuille du bas sur téléphone.
Future<void> showAppSheet(BuildContext context, {required List<Widget> Function(AppPalette p) children}) {
  if (isWide(context)) {
    return showDialog<void>(
      context: context,
      useRootNavigator: true,
      builder: (ctx) {
        final p = AppPalette.of(ctx);
        return Dialog(
          backgroundColor: p.panel,
          surfaceTintColor: Colors.transparent,
          insetPadding: const EdgeInsets.all(32),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: 560, maxHeight: MediaQuery.sizeOf(ctx).height * .85),
            child: Stack(children: [
              ListView(
                shrinkWrap: true,
                padding: const EdgeInsets.fromLTRB(32, 36, 32, 36),
                children: children(p),
              ),
              Positioned(
                top: 12,
                right: 12,
                child: IconButton(
                  tooltip: 'Fermer',
                  onPressed: () => Navigator.pop(ctx),
                  icon: Icon(Icons.close_rounded, color: p.text2),
                ),
              ),
            ]),
          ),
        );
      },
    );
  }
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
            color: p.panel,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          ),
          child: ListView(
            controller: scroll,
            padding: const EdgeInsets.fromLTRB(24, 10, 24, 40),
            children: [
              Center(
                child: Container(
                  width: 36,
                  height: 5,
                  decoration: BoxDecoration(color: p.separator, borderRadius: BorderRadius.circular(3)),
                ),
              ),
              const SizedBox(height: 22),
              ...children(p),
            ],
          ),
        ),
      );
    },
  );
}

Future<void> showCapsuleSheet(BuildContext context, CultureCapsule c) => showAppSheet(context,
    children: (p) => [
          _Label('Culture · ${c.title}', color: p.gold),
          const SizedBox(height: 8),
          Text(c.kab.isNotEmpty ? c.kab : c.title, style: AppTheme.serif(size: 30, color: p.text)),
          const SizedBox(height: 14),
          Text(c.body, style: TextStyle(fontSize: 17, height: 1.55, color: p.text)),
          const SizedBox(height: 28),
          Center(child: AmusnawMark(size: 34, color: p.gold)),
        ]);

Future<void> showWordSheet(BuildContext context, WordOfTheDay w) => showAppSheet(context,
    children: (p) => [
          const _Label('Mot du jour'),
          const SizedBox(height: 10),
          Text(w.word, style: AppTheme.serif(size: 44, color: p.text)),
          if (w.tifinagh.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(w.tifinagh, style: AppTheme.tifinagh(size: 22, color: p.accentText).copyWith(letterSpacing: 3)),
          ],
          const SizedBox(height: 14),
          Text(w.meaning, style: TextStyle(fontSize: 20, color: p.text2)),
          const SizedBox(height: 24),
          Text('Essaie de l’employer dans une conversation un autre jour : il comptera alors dans tes mots appris.',
              style: TextStyle(fontSize: 15, height: 1.45, color: p.text2)),
        ]);

/// Exercice compact à choix, affiché dans le chat.
class InlineExercise extends StatefulWidget {
  const InlineExercise({super.key, required this.exercise, this.onCorrect});
  final ChoiceExercise exercise;
  final VoidCallback? onCorrect;

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

  Widget _option(AppPalette p, String o) {
    final picked = _picked == o;
    final right = o == widget.exercise.answer;
    return GestureDetector(
      onTap: () => _pick(o),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        constraints: const BoxConstraints(minHeight: 44),
        alignment: Alignment.center,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          color: picked ? (right ? p.greenSoft : p.goldSoft) : p.fill,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: picked ? (right ? p.green : p.gold) : Colors.transparent, width: 1.5),
        ),
        child: Text(o,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              color: picked ? (right ? p.green : p.gold) : (_done ? p.text2 : p.text),
              fontWeight: picked ? FontWeight.w600 : FontWeight.w400,
            )),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final ex = widget.exercise;
    final short = ex.options.every((o) => o.length <= 10);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: cardDecoration(p),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _Label('Exercice'),
          const SizedBox(height: 6),
          Text(ex.hasBlank ? '${ex.before}_____${ex.after}' : ex.before,
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600, color: p.text, letterSpacing: -.3)),
          if (ex.tifinagh != null && ex.tifinagh!.isNotEmpty)
            ExcludeSemantics(
              child: Text(ex.tifinagh!,
                  style: AppTheme.tifinagh(size: 13, color: p.text2).copyWith(letterSpacing: 2)),
            ),
          const SizedBox(height: 12),
          if (short)
            Row(children: [
              for (var i = 0; i < ex.options.length; i++) ...[
                if (i > 0) const SizedBox(width: 8),
                Expanded(child: _option(p, ex.options[i])),
              ],
            ])
          else
            Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              for (var i = 0; i < ex.options.length; i++) ...[
                if (i > 0) const SizedBox(height: 8),
                _option(p, ex.options[i]),
              ],
            ]),
          if (_picked != null) ...[
            const SizedBox(height: 10),
            Text(
              _done ? ex.explanation : 'Pas tout à fait — essaie une autre réponse.',
              style: TextStyle(fontSize: 14, height: 1.4, color: _done ? p.green : p.gold),
            ),
          ],
        ],
      ),
    );
  }
}

/// Bouton rond flottant (menu, thème) de la barre du haut.
class RoundIconButton extends StatelessWidget {
  const RoundIconButton({super.key, required this.icon, required this.label, required this.onPressed});
  final Widget icon;
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Semantics(
      label: label,
      button: true,
      child: GestureDetector(
        onTap: onPressed,
        child: Container(
          width: 44,
          height: 44,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: p.surface,
            shape: BoxShape.circle,
            border: Border.all(color: p.separator, width: .5),
            boxShadow: p.shadow,
          ),
          child: icon,
        ),
      ),
    );
  }
}

/// Icône « menu » à deux traits, comme sur la maquette.
class MenuGlyph extends StatelessWidget {
  const MenuGlyph({super.key, required this.color});
  final Color color;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 18,
        height: 12,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(width: 18, height: 1.8, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(1))),
            Container(width: 11, height: 1.8, decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(1))),
          ],
        ),
      );
}

const kCupertinoChevron = CupertinoIcons.chevron_right;
