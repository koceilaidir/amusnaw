import 'package:flutter/material.dart';

import 'google_button_stub.dart' if (dart.library.js_interop) 'google_button_web.dart' as impl;

/// Bouton « Continuer avec Google ».
/// - Téléphone : notre bouton, qui ouvre la connexion Google du système.
/// - Site web : le bouton officiel de Google (obligatoire dans un navigateur) ;
///   la session arrive alors par `authService.webGoogleSessions`.
class GoogleButton extends StatelessWidget {
  const GoogleButton({super.key, required this.onPressed});

  /// Téléphone seulement (sur le web, Google gère le clic).
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => impl.googleButton(context, onPressed);
}
