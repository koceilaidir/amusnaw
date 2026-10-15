import 'package:flutter/cupertino.dart';

import '../../features/onboarding/welcome_screen.dart';
import '../content/content_repository.dart';
import '../learning/learner_store.dart';
import '../notifications/reminder_service.dart';
import '../settings/app_settings.dart';
import 'auth_service.dart';

/// Déconnexion (ou compte supprimé / jeton expiré) : on efface les données
/// locales et on revient à l'accueil.
Future<void> endSession(BuildContext context) async {
  final nav = Navigator.of(context, rootNavigator: true);
  await authService.signOut().catchError((_) {});
  await learnerStore.reset();
  await reminderService.cancel().catchError((_) {});
  await appSettings.reset();
  contentRepository.clear();
  nav.pushAndRemoveUntil(
    CupertinoPageRoute(builder: (_) => const WelcomeScreen()),
    (_) => false,
  );
}
