import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

/// Couleurs d'accent proposées dans le menu Thème (en haut à droite).
class AccentChoice {
  const AccentChoice(this.id, this.label, this.light, this.lightText, this.lightSoft, this.dark, this.darkSoft);
  final String id, label;
  final Color light, lightText, lightSoft, dark, darkSoft;
}

/// Couleur principale : le vert olivier (seule couleur de l'app).
const accentChoices = <AccentChoice>[
  AccentChoice('olivier', 'Olivier', Color(0xFF56662E), Color(0xFF4E5C29), Color(0xFFE7ECD9), Color(0xFFA9BD72),
      Color(0xFF283020)),
];

AccentChoice accentById(String? id) =>
    accentChoices.firstWhere((a) => a.id == id, orElse: () => accentChoices.first);

/// Palette de la maquette V2 : tons pierre chauds, une couleur d'accent.
/// Attachée au thème (ThemeExtension) : `AppPalette.of(context)`.
class AppPalette extends ThemeExtension<AppPalette> {
  const AppPalette({
    required this.bgTop,
    required this.bg,
    required this.surface,
    required this.panel,
    required this.bubble,
    required this.fill,
    required this.text,
    required this.text2,
    required this.separator,
    required this.ink,
    required this.onInk,
    required this.accent,
    required this.accentText,
    required this.accentSoft,
    required this.onAccent,
    required this.gold,
    required this.goldSoft,
    required this.green,
    required this.greenSoft,
    required this.isDark,
  });

  final Color bgTop, bg, surface, panel, bubble, fill, text, text2, separator, ink, onInk;
  final Color accent, accentText, accentSoft, onAccent, gold, goldSoft, green, greenSoft;
  final bool isDark;

  factory AppPalette.build(Brightness b, AccentChoice a) => b == Brightness.dark
      ? AppPalette(
          bgTop: const Color(0xFF231F1B),
          bg: const Color(0xFF141312),
          surface: const Color(0xFF1E1D1B),
          panel: const Color(0xFF1E1D1B),
          bubble: const Color(0xFF2B2926),
          fill: const Color(0xFF2B2926),
          text: const Color(0xFFF3EFE8),
          text2: const Color(0xFFABA59C),
          separator: const Color(0xFF36332F),
          ink: const Color(0xFFF3EFE8),
          onInk: const Color(0xFF141312),
          accent: a.dark,
          accentText: a.dark,
          accentSoft: a.darkSoft,
          onAccent: const Color(0xFF1A120C),
          gold: const Color(0xFFE0BC74),
          goldSoft: const Color(0xFF2E2717),
          green: const Color(0xFF7BC897),
          greenSoft: const Color(0xFF1E2E24),
          isDark: true,
        )
      : AppPalette(
          bgTop: const Color(0xFFEFE7DC),
          bg: const Color(0xFFF6F4F0),
          surface: const Color(0xFFFFFFFF),
          panel: const Color(0xFFFBFAF8),
          bubble: const Color(0xFFECE8E1),
          fill: const Color(0xFFEEEBE5),
          text: const Color(0xFF1D1B18),
          text2: const Color(0xFF6B675F),
          separator: const Color(0xFFE3DED5),
          ink: const Color(0xFF1D1B18),
          onInk: const Color(0xFFFAF8F4),
          accent: a.light,
          accentText: a.lightText,
          accentSoft: a.lightSoft,
          onAccent: const Color(0xFFFFFFFF),
          gold: const Color(0xFF7A5A12),
          goldSoft: const Color(0xFFF4ECD9),
          green: const Color(0xFF2A7448),
          greenSoft: const Color(0xFFE1EFE5),
          isDark: false,
        );

  /// Ombre douce des cartes (aucune en sombre, la bordure suffit).
  List<BoxShadow> get shadow => isDark
      ? const []
      : const [
          BoxShadow(color: Color(0x0D1D1B18), blurRadius: 2, offset: Offset(0, 1)),
          BoxShadow(color: Color(0x0D1D1B18), blurRadius: 20, offset: Offset(0, 6)),
        ];

  List<BoxShadow> get shadowLg => isDark
      ? const [BoxShadow(color: Color(0x59000000), blurRadius: 30, offset: Offset(0, 10))]
      : const [
          BoxShadow(color: Color(0x0F1D1B18), blurRadius: 2, offset: Offset(0, 1)),
          BoxShadow(color: Color(0x141D1B18), blurRadius: 32, offset: Offset(0, 12)),
        ];

  static AppPalette of(BuildContext context) =>
      Theme.of(context).extension<AppPalette>() ??
      AppPalette.build(Theme.of(context).brightness, accentChoices.first);

  @override
  AppPalette copyWith() => this;

  @override
  AppPalette lerp(ThemeExtension<AppPalette>? other, double t) =>
      other is AppPalette && t > .5 ? other : this;
}

class AppTheme {
  static const font = 'Onest';
  static const tifinaghFont = 'NotoSansTifinagh';

  /// Titres (Azul, mots kabyles). Onest affiche ɛ ɣ ḍ ṭ ẓ ṛ ṣ ḥ č ǧ.
  static TextStyle serif({double size = 28, Color? color}) => TextStyle(
        fontFamily: font,
        fontSize: size,
        color: color,
        height: 1.15,
        fontWeight: FontWeight.w500,
        letterSpacing: -size * .025,
      );

  /// Tifinagh (mot du jour, cartes).
  static TextStyle tifinagh({double size = 20, Color? color}) =>
      TextStyle(fontFamily: tifinaghFont, fontSize: size, color: color);

  static ThemeData build(Brightness b, AccentChoice accent) {
    final p = AppPalette.build(b, accent);
    final base = ThemeData(
      useMaterial3: true,
      brightness: b,
      fontFamily: font,
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
      extensions: [p],
    );
    return base.copyWith(
      textTheme: base.textTheme.apply(fontFamily: font, bodyColor: p.text, displayColor: p.text),
      cupertinoOverrideTheme: CupertinoThemeDataFont.of(p, b),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: p.accent,
          foregroundColor: p.onAccent,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
          textStyle: const TextStyle(fontFamily: font, fontSize: 17, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: p.text,
          backgroundColor: p.surface,
          minimumSize: const Size.fromHeight(52),
          side: BorderSide(color: p.separator),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
          textStyle: const TextStyle(fontFamily: font, fontSize: 17, fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}

/// Police Onest aussi pour les widgets Cupertino (listes, barres).
class CupertinoThemeDataFont {
  static NoDefaultCupertinoThemeData of(AppPalette p, Brightness b) => NoDefaultCupertinoThemeData(
        brightness: b,
        primaryColor: p.accent,
        scaffoldBackgroundColor: p.bg,
        barBackgroundColor: p.bg.withValues(alpha: .92),
        textTheme: CupertinoTextThemeData(
          primaryColor: p.accent,
          textStyle: TextStyle(fontFamily: AppTheme.font, fontSize: 17, color: p.text, letterSpacing: -.2),
          navLargeTitleTextStyle: TextStyle(
              fontFamily: AppTheme.font, fontSize: 32, fontWeight: FontWeight.w600, color: p.text, letterSpacing: -.8),
          navTitleTextStyle:
              TextStyle(fontFamily: AppTheme.font, fontSize: 17, fontWeight: FontWeight.w600, color: p.text),
          actionTextStyle: TextStyle(fontFamily: AppTheme.font, fontSize: 17, color: p.accentText),
        ),
      );
}
