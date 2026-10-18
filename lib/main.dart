import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/auth/auth_service.dart';
import 'core/chat/conversation_store.dart';
import 'core/learning/learner_store.dart';
import 'core/locale/locale_controller.dart';
import 'core/notifications/reminder_service.dart';
import 'core/settings/app_settings.dart';
import 'features/tutor/tutor_chat_screen.dart';
import 'features/onboarding/welcome_screen.dart';
import 'theme/app_theme.dart';

/// Plein écran : barre d'état (en haut) et barre de navigation (en bas)
/// cachées. Un glissement depuis le bord les fait réapparaître un instant.
void _fullscreen() => SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);

// Android réaffiche parfois les barres au retour dans l'app : on les recache.
// ignore: unused_element
late final AppLifecycleListener _lifecycle;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  _fullscreen();
  _lifecycle = AppLifecycleListener(onResume: _fullscreen);
  await initializeDateFormatting(); // dates dans la langue du prof
  final prefs = await SharedPreferences.getInstance();
  localeController.load(prefs);
  appSettings.load(prefs);
  await learnerStore.load(prefs);
  conversationStore.load(prefs);
  String? token;
  try {
    token = await authService.currentToken();
  } catch (_) {/* stockage sécurisé illisible : on redemande la connexion */}
  // Site web : comme les autres IA, on peut utiliser Amusnaw tout de suite, sans compte.
  // Un compte est proposé ensuite pour garder sa progression et ses discussions.
  if (token == null && kIsWeb) {
    try {
      await authService.signInForTesting(name: '');
      token = await authService.currentToken();
    } catch (_) {/* serveur injoignable : l'accueil s'affiche */}
  }
  if (token != null) conversationStore.syncWithServer(); // discussions des autres appareils
  // Reprogramme le rappel (fuseau ou langue ont pu changer).
  final s = appSettings.value;
  if (s.reminderOn) {
    reminderService.schedule(s.reminderTime, localeController.value.code).catchError((_) {});
  }
  runApp(AmusnawApp(signedIn: token != null));
}

class AmusnawApp extends StatelessWidget {
  const AmusnawApp({super.key, this.signedIn = false});

  /// Déjà connecté : on ouvre directement l'app (le jeton est revérifié
  /// par l’écran de chat ; s'il a expiré, retour à l'accueil).
  final bool signedIn;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([localeController, appSettings]),
      builder: (context, _) => MaterialApp(
        title: 'Amusnaw',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.build(Brightness.light, accentById(appSettings.value.accent)),
        darkTheme: AppTheme.build(Brightness.dark, accentById(appSettings.value.accent)),
        themeMode: appSettings.value.themeMode,
        locale: localeController.locale,
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: [
          for (final l in supportedTutorLanguages) Locale(l.code),
        ],
        home: signedIn ? const TutorChatScreen() : const WelcomeScreen(),
      ),
    );
  }
}
