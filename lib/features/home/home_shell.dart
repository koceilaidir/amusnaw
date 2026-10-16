import 'package:flutter/widgets.dart';

import '../tutor/tutor_chat_screen.dart';

/// Ancien écran à onglets, remplacé par le chat (design V2).
/// Gardé pour compatibilité : il ouvre simplement le chat.
class HomeShell extends StatelessWidget {
  const HomeShell({super.key});

  @override
  Widget build(BuildContext context) => const TutorChatScreen();
}
