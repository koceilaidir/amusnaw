import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Palette de la maquette, inspirée des couleurs système iOS.
/// Couleur principale : indigo amazigh (modifiable ici uniquement).
class AppPalette {
  const AppPalette({
    required this.bg,
    required this.surface,
    required this.text,
    required this.text2,
    required this.separator,
    required this.fill,
    required this.accent,
    required this.onAccent,
    required this.gold,
    required this.goldSoft,
    required this.green,
    required this.greenSoft,
  });

  final Color bg, surface, text, text2, separator, fill;
  final Color accent, onAccent, gold, goldSoft, green, greenSoft;

  static const light = AppPalette(
    bg: Color(0xFFF2F2F7),
    surface: Color(0xFFFFFFFF),
    text: Color(0xFF000000),
    text2: Color(0xFF6C6C70),
    separator: Color(0xFFC6C6C8),
    fill: Color(0xFFE3E3E8),
    accent: Color(0xFF2F54C8),
    onAccent: Color(0xFFFFFFFF),
    gold: Color(0xFF7A5A12),
    goldSoft: Color(0xFFF6EEDB),
    green: Color(0xFF1F7A35),
    greenSoft: Color(0xFFE2F3E6),
  );

  static const dark = AppPalette(
    bg: Color(0xFF000000),
    surface: Color(0xFF1C1C1E),
    text: Color(0xFFFFFFFF),
    text2: Color(0xFFAEAEB2),
    separator: Color(0xFF38383A),
    fill: Color(0xFF2C2C2E),
    accent: Color(0xFF7D97F5),
    onAccent: Color(0xFF0A1230),
    gold: Color(0xFFE6C27A),
    goldSoft: Color(0xFF2A2416),
    green: Color(0xFF30D158),
    greenSoft: Color(0xFF0E2A17),
  );

  static AppPalette of(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? dark : light;
}

class AppTheme {
  /// Titres « éditoriaux » (Azul., mots kabyles) — couvre ɛ ɣ ḍ ṭ ẓ ṛ ṣ ḥ č ǧ.
  static TextStyle serif({double size = 28, Color? color}) =>
      GoogleFonts.notoSerif(fontSize: size, color: color, height: 1.15);

  /// Tifinagh pour logo et filigranes.
  static TextStyle tifinagh({double size = 20, Color? color}) =>
      GoogleFonts.getFont('Noto Sans Tifinagh', fontSize: size, color: color);

  static ThemeData light() => _build(AppPalette.light, Brightness.light);
  static ThemeData dark() => _build(AppPalette.dark, Brightness.dark);

  static ThemeData _build(AppPalette p, Brightness b) {
    final base = ThemeData(
      useMaterial3: true,
      brightness: b,
      // Comportements iOS (retour par glissement, rebond) sur toutes les plateformes.
      platform: TargetPlatform.iOS,
      colorScheme: ColorScheme.fromSeed(
        seedColor: p.accent,
        brightness: b,
        primary: p.accent,
        onPrimary: p.onAccent,
        surface: p.surface,
        onSurface: p.text,
      ),
      scaffoldBackgroundColor: p.bg,
      dividerColor: p.separator,
      splashFactory: NoSplash.splashFactory,
      highlightColor: Colors.transparent,
    );
    // Sur iPhone, la police système (SF Pro) est utilisée automatiquement ;
    // Noto Sans sert de repli ailleurs.
    final text = GoogleFonts.notoSansTextTheme(base.textTheme)
        .apply(bodyColor: p.text, displayColor: p.text);
    return base.copyWith(
      textTheme: text,
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: p.accent,
          foregroundColor: p.onAccent,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: p.text,
          backgroundColor: p.surface,
          minimumSize: const Size.fromHeight(52),
          side: BorderSide(color: p.separator),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
