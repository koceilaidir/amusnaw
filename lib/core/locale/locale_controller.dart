import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';

/// Langue dans laquelle le prof explique.
/// Au premier lancement : langue du téléphone si elle est supportée,
/// sinon anglais. L'utilisateur peut ensuite la changer.
class TutorLanguage {
  const TutorLanguage(this.code, this.label, this.line);
  final String code;
  final String label;

  /// Phrase affichée sur l'accueil (« Je te parlerai en français. »).
  final String line;
}

const supportedTutorLanguages = <TutorLanguage>[
  TutorLanguage('en', 'English', 'I’ll speak with you in English.'),
  TutorLanguage('fr', 'Français', 'Je te parlerai en français.'),
  TutorLanguage('ar', 'العربية', 'سأتحدث معك بالعربية.'),
  TutorLanguage('es', 'Español', 'Te hablaré en español.'),
  TutorLanguage('de', 'Deutsch', 'Ich spreche Deutsch mit dir.'),
];

class LocaleController extends ValueNotifier<TutorLanguage> {
  LocaleController() : super(_detect());

  static TutorLanguage _detect() {
    final deviceCode = PlatformDispatcher.instance.locale.languageCode;
    return supportedTutorLanguages.firstWhere(
      (l) => l.code == deviceCode,
      // langue non proposée (chinois, kabyle…) : le français, langue de l'interface
      orElse: () => supportedTutorLanguages.firstWhere((l) => l.code == 'fr'),
    );
  }

  /// Vrai tant que l'utilisateur n'a pas choisi lui-même.
  bool detected = true;

  Locale get locale => Locale(value.code);

  static const _key = 'tutor_language';
  SharedPreferences? _prefs;

  void load(SharedPreferences prefs) {
    _prefs = prefs;
    final code = prefs.getString(_key);
    if (code == null) return;
    detected = false;
    value = supportedTutorLanguages.firstWhere((l) => l.code == code, orElse: () => value);
  }

  /// Choix de l'utilisateur : enregistré sur le téléphone et envoyé au
  /// serveur (le prof explique dans cette langue).
  void choose(TutorLanguage lang, {bool syncServer = false}) {
    detected = false;
    value = lang;
    _prefs?.setString(_key, lang.code);
    if (syncServer) {
      api.patch('/me/language', {'interface_language': lang.code}).catchError((_) => <String, dynamic>{});
    }
  }
}

final localeController = LocaleController();
