import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'app_theme.dart';

/// Aquarelles kabyles (vallée, olivier, plaine, brume) posées en filigrane.
/// Peintes sur papier clair : en mode sombre on les fond beaucoup plus.
enum Fond {
  vallee('assets/fonds/vallee.webp'),
  olivier('assets/fonds/paysage-olivier.webp'),
  plaine('assets/fonds/paysage-plaine.webp'),
  brume('assets/fonds/brume.webp');

  const Fond(this.asset);
  final String asset;
}

/// À placer dans un Stack, sous le contenu :
/// `Aquarelle(Fond.plaine, opacity: .4)` remplit tout l'espace, image calée en bas.
class Aquarelle extends StatelessWidget {
  const Aquarelle(this.fond, {super.key, this.opacity = .4, this.alignment = Alignment.bottomCenter,
      this.fit = BoxFit.cover, this.height});

  final Fond fond;
  final double opacity;
  final Alignment alignment;
  final BoxFit fit;

  /// Hauteur de la bande en bas ; null = tout l'espace.
  final double? height;

  @override
  Widget build(BuildContext context) {
    final dark = AppPalette.of(context).isDark;
    final img = Image.asset(
      fond.asset,
      fit: fit,
      alignment: alignment,
      width: double.infinity,
      height: height ?? double.infinity,
      opacity: AlwaysStoppedAnimation(dark ? opacity * .22 : opacity),
      filterQuality: FilterQuality.medium,
      gaplessPlayback: true,
      excludeFromSemantics: true,
      errorBuilder: (_, __, ___) => const SizedBox.shrink(),
    );
    final child = IgnorePointer(child: ExcludeSemantics(child: img));
    if (height == null) return Positioned.fill(child: child);
    return Positioned(left: 0, right: 0, bottom: 0, height: height, child: child);
  }
}

/// Rosace inspirée de la fibule kabyle (tabzimt) : cercles, couronne de
/// triangles, perles, pétales en losange et ⵣ au centre.
/// Toujours très discrète (opacity 0.05–0.15), souvent coupée par le bord.
///
/// Positioned(top: -110, right: -130, child: Rosette(size: 340, opacity: .12))
class Rosette extends StatelessWidget {
  const Rosette({
    super.key,
    this.size = 300,
    this.opacity = 0.12,
    this.color,
  });

  final double size;
  final double opacity;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.primary;
    return ExcludeSemantics(
      child: IgnorePointer(
        child: Opacity(
          opacity: opacity,
          child: CustomPaint(
            size: Size.square(size),
            painter: _RosettePainter(c),
          ),
        ),
      ),
    );
  }
}

class _RosettePainter extends CustomPainter {
  _RosettePainter(this.color);
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    // Dessin sur une grille 300×300 puis mise à l'échelle.
    final s = size.width / 300;
    canvas.scale(s);
    const c = Offset(150, 150);

    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1 / s;
    final fill = Paint()..color = color;

    canvas.drawCircle(c, 146, stroke);
    canvas.drawCircle(c, 128, stroke);
    canvas.drawCircle(c, 40, stroke);
    _dashedCircle(canvas, c, 112, stroke);

    void rotated(double deg, void Function() draw) {
      canvas.save();
      canvas.translate(c.dx, c.dy);
      canvas.rotate(deg * math.pi / 180);
      canvas.translate(-c.dx, -c.dy);
      draw();
      canvas.restore();
    }

    final triangle = Path()
      ..moveTo(150, 25)
      ..lineTo(156, 36)
      ..lineTo(144, 36)
      ..close();
    final petal = Path()
      ..moveTo(150, 62)
      ..lineTo(161, 88)
      ..lineTo(150, 110)
      ..lineTo(139, 88)
      ..close();
    final smallPetal = Path()
      ..moveTo(150, 76)
      ..lineTo(155, 90)
      ..lineTo(150, 102)
      ..lineTo(145, 90)
      ..close();

    for (var i = 0; i < 24; i++) {
      rotated(i * 15.0, () => canvas.drawPath(triangle, fill));
      rotated(i * 15.0 + 7.5,
          () => canvas.drawCircle(const Offset(150, 13), 2, fill));
    }
    for (var i = 0; i < 8; i++) {
      rotated(i * 45.0, () => canvas.drawPath(petal, stroke));
      rotated(i * 45.0 + 22.5, () => canvas.drawPath(smallPetal, stroke));
    }

    final tp = TextPainter(
      text: TextSpan(
        text: 'ⵣ',
        style: AppTheme.tifinagh(size: 46, color: color),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, c - Offset(tp.width / 2, tp.height / 2));
  }

  void _dashedCircle(Canvas canvas, Offset c, double r, Paint p) {
    const dash = 2.0, gap = 5.0;
    final circumference = 2 * math.pi * r;
    final steps = (circumference / (dash + gap)).floor();
    for (var i = 0; i < steps; i++) {
      final a0 = i * (dash + gap) / r;
      canvas.drawArc(Rect.fromCircle(center: c, radius: r), a0, dash / r,
          false, p);
    }
  }

  @override
  bool shouldRepaint(covariant _RosettePainter old) => old.color != color;
}

/// Paysage kabyle en filigrane, posé en bas d'un écran : collines et plaine,
/// un olivier, un figuier de Barbarie, et une frise de motifs berbères
/// (losanges et chevrons des tapis et poteries). Très discret, en une couleur.
class KabyleLandscape extends StatelessWidget {
  const KabyleLandscape({super.key, this.height = 260, this.opacity = 0.10, this.color, this.frieze = true});

  final double height;
  final double opacity;
  final Color? color;
  final bool frieze;

  @override
  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.primary;
    return ExcludeSemantics(
      child: IgnorePointer(
        child: Opacity(
          opacity: opacity,
          child: SizedBox(
            height: height,
            width: double.infinity,
            child: CustomPaint(painter: _LandscapePainter(c, frieze)),
          ),
        ),
      ),
    );
  }
}

class _LandscapePainter extends CustomPainter {
  _LandscapePainter(this.color, this.frieze);
  final Color color;
  final bool frieze;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    final fill = Paint()..color = color;
    final soft = Paint()..color = color.withValues(alpha: .55);
    final line = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    // Frise berbère (losanges, points, chevrons) au-dessus du paysage
    if (frieze) {
      final y = h * .12, s = 18.0;
      line.strokeWidth = 1.6;
      for (var x = s; x < w; x += s * 2.4) {
        final d = Path()
          ..moveTo(x, y - s * .7)
          ..lineTo(x + s * .7, y)
          ..lineTo(x, y + s * .7)
          ..lineTo(x - s * .7, y)
          ..close();
        canvas.drawPath(d, line);
        canvas.drawCircle(Offset(x, y), 2.2, fill);
        final cx = x + s * 1.2; // chevron entre deux losanges
        canvas.drawPath(
            Path()
              ..moveTo(cx - 5, y - 6)
              ..lineTo(cx, y)
              ..lineTo(cx - 5, y + 6),
            line);
      }
      canvas.drawLine(Offset(0, y - s), Offset(w, y - s), line..strokeWidth = 1);
      canvas.drawLine(Offset(0, y + s), Offset(w, y + s), line);
    }

    // Collines du fond, puis plaine au premier plan
    final back = Path()
      ..moveTo(0, h * .62)
      ..cubicTo(w * .22, h * .48, w * .45, h * .70, w * .68, h * .56)
      ..cubicTo(w * .82, h * .48, w * .92, h * .55, w, h * .52)
      ..lineTo(w, h)
      ..lineTo(0, h)
      ..close();
    canvas.drawPath(back, soft);
    final front = Path()
      ..moveTo(0, h * .80)
      ..cubicTo(w * .30, h * .70, w * .62, h * .88, w, h * .76)
      ..lineTo(w, h)
      ..lineTo(0, h)
      ..close();
    canvas.drawPath(front, fill);

    // Brins d'herbe sur la plaine
    line.strokeWidth = 1.4;
    for (var x = 8.0; x < w; x += 23) {
      final t = x / w;
      final base = h * (.80 + (math.sin(t * math.pi * 2.2) * .05)) + 4;
      canvas.drawLine(Offset(x, base), Offset(x - 3, base - 9), line);
      canvas.drawLine(Offset(x + 4, base), Offset(x + 6, base - 7), line);
    }

    // Olivier (tronc tourmenté, feuillage en grappes) sur la colline de droite
    final ox = w * .80, oy = h * .53;
    final trunk = Path()
      ..moveTo(ox - 10, oy + 6)
      ..cubicTo(ox - 4, oy - 20, ox - 18, oy - 38, ox - 6, oy - 58)
      ..lineTo(ox + 4, oy - 56)
      ..cubicTo(ox - 4, oy - 36, ox + 12, oy - 20, ox + 8, oy + 6)
      ..close();
    canvas.drawPath(trunk, fill);
    line.strokeWidth = 5;
    canvas.drawLine(Offset(ox - 4, oy - 50), Offset(ox - 30, oy - 72), line);
    canvas.drawLine(Offset(ox, oy - 52), Offset(ox + 26, oy - 76), line);
    for (final (dx, dy, r) in const [
      (-46.0, -84.0, 20.0), (-24.0, -98.0, 24.0), (4.0, -104.0, 26.0), (32.0, -94.0, 22.0),
      (50.0, -78.0, 17.0), (-34.0, -70.0, 16.0), (18.0, -76.0, 20.0), (-8.0, -80.0, 18.0),
    ]) {
      canvas.drawOval(Rect.fromCenter(center: Offset(ox + dx, oy + dy), width: r * 2.3, height: r * 1.6), fill);
    }

    // Figuier de Barbarie (raquettes ovales, épines, fruits) à gauche
    final fx = w * .13, fy = h * .74;
    void pad(double cx, double cy, double pw, double ph, double angle) {
      canvas.save();
      canvas.translate(cx, cy);
      canvas.rotate(angle);
      canvas.drawOval(Rect.fromCenter(center: Offset.zero, width: pw, height: ph), fill);
      canvas.restore();
    }

    pad(fx, fy - 26, 34, 52, 0);
    pad(fx - 24, fy - 66, 30, 44, -.45);
    pad(fx + 22, fy - 70, 30, 46, .4);
    pad(fx - 2, fy - 100, 26, 38, .1);
    for (final (dx, dy) in const [(-30.0, -92.0), (34.0, -96.0), (-6.0, -122.0), (10.0, -120.0)]) {
      canvas.drawOval(Rect.fromCenter(center: Offset(fx + dx, fy + dy), width: 9, height: 12), fill);
    }
  }

  @override
  bool shouldRepaint(covariant _LandscapePainter old) => old.color != color || old.frieze != frieze;
}
