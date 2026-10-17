import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../theme/mark.dart';

/// Carte arrondie iOS (fond « secondary grouped »).
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.color,
    this.radius = 20,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? color;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color ?? p.surface,
        borderRadius: BorderRadius.circular(radius),
        border: color == null ? Border.all(color: p.separator, width: .5) : null,
        boxShadow: color == null ? p.shadow : null,
      ),
      child: child,
    );
  }
}

/// Petite icône sur fond teinté (style Réglages iOS).
class TintIcon extends StatelessWidget {
  const TintIcon(this.icon, {super.key, this.size = 30});
  final IconData icon;
  final double size;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: p.accentSoft,
        borderRadius: BorderRadius.circular(size * .3),
      ),
      child: Icon(icon, size: size * .55, color: p.accentText),
    );
  }
}

/// Légende en capitales grises au-dessus d'un bloc.
class Caption extends StatelessWidget {
  const Caption(this.text, {super.key, this.color});
  final String text;
  final Color? color;

  @override
  Widget build(BuildContext context) => Text(
        text.toUpperCase(),
        style: TextStyle(
          fontSize: 12.5,
          fontWeight: FontWeight.w600,
          letterSpacing: .2,
          color: color ?? AppPalette.of(context).text2,
        ),
      );
}

/// Avatar du prof : le symbole d'Amusnaw.
class TutorAvatar extends StatelessWidget {
  const TutorAvatar({super.key, this.size = 36});
  final double size;

  @override
  Widget build(BuildContext context) => AmusnawMark(size: size, color: AppPalette.of(context).text);
}

/// Bouton principal plein largeur.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.label, required this.onPressed});
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: double.infinity,
        child: FilledButton(onPressed: onPressed, child: Text(label)),
      );
}

/// Barre de navigation iOS aux couleurs de l'app.
CupertinoSliverNavigationBar largeTitleBar(BuildContext context, String title,
    {Widget? trailing}) {
  final p = AppPalette.of(context);
  return CupertinoSliverNavigationBar(
    largeTitle: Text(title, style: TextStyle(color: p.text)),
    backgroundColor: p.bg.withValues(alpha: .92),
    border: null,
    trailing: trailing,
  );
}


/// Grand écran (ordinateur, tablette en paysage) : menu fixe à gauche,
/// contenu à largeur de lecture.
const kWideBreakpoint = 900.0;

bool isWide(BuildContext context) => MediaQuery.sizeOf(context).width >= kWideBreakpoint;

/// Centre le contenu à une largeur de lecture confortable sur grand écran.
class ReadingWidth extends StatelessWidget {
  const ReadingWidth({super.key, required this.child, this.maxWidth = 760});
  final Widget child;
  final double maxWidth;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, c) => Align(
          alignment: Alignment.topCenter,
          child: SizedBox(
            // pleine hauteur quand elle est connue (listes, pages), largeur limitée
            width: c.maxWidth < maxWidth ? c.maxWidth : maxWidth,
            height: c.hasBoundedHeight ? c.maxHeight : null,
            child: child,
          ),
        ),
      );
}
