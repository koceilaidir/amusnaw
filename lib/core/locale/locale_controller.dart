import 'dart:ui';

import 'package:flutter/foundation.dart';

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
      orElse: () => supportedTutorLanguages.first,
    );
  }

  /// Vrai tant que l'utilisateur n'a pas choisi lui-même.
  bool detected = true;

  Locale get locale => Locale(value.code);

  void choose(TutorLanguage lang) {
    detected = false;
    value = lang;
    // TODO: persister le choix (shared_preferences) et l'envoyer au serveur.
  }
}

final localeController = LocaleController();
