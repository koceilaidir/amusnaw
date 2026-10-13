import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'app_theme.dart';

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
