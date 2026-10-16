import 'package:flutter/material.dart';

/// Le symbole d'Amusnaw : l'étoile amazighe (deux grandes branches croisées,
/// un V de chaque côté et une petite branche intérieure), en traits arrondis.
/// Dessiné dans une boîte 108 × 100 (même tracé que la maquette).
class AmusnawMark extends StatelessWidget {
  const AmusnawMark({super.key, this.size = 28, this.color});

  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'Amusnaw',
        image: true,
        child: CustomPaint(
          size: Size.square(size),
          painter: _MarkPainter(color ?? DefaultTextStyle.of(context).style.color ?? Colors.black),
        ),
      );
}

class _MarkPainter extends CustomPainter {
  _MarkPainter(this.color);
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    // viewBox -4 -1 108 100
    final s = size.width / 108;
    canvas.save();
    canvas.translate(4 * s, 1 * s + (size.height - 100 * s) / 2);
    canvas.scale(s);
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 11
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final right = Path()
      ..moveTo(36, 18)
      ..lineTo(71, 70)
      ..quadraticBezierTo(76, 78, 80, 71)
      ..lineTo(91, 57);
    final left = Path()
      ..moveTo(64, 18)
      ..lineTo(29, 70)
      ..quadraticBezierTo(24, 78, 20, 71)
      ..lineTo(9, 57);
    final branchL = Path()
      ..moveTo(21, 36)
      ..lineTo(39, 55);
    final branchR = Path()
      ..moveTo(79, 36)
      ..lineTo(61, 55);
    for (final p in [right, left, branchL, branchR]) {
      canvas.drawPath(p, paint);
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(_MarkPainter old) => old.color != color;
}
