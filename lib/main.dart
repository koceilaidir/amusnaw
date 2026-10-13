import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'core/locale/locale_controller.dart';
import 'features/onboarding/welcome_screen.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting(); // dates dans la langue du prof
  runApp(const AmusnawApp());
}

class AmusnawApp extends StatelessWidget {
  const AmusnawApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder(
      valueListenable: localeController,
      builder: (context, _, __) => MaterialApp(
        title: 'Amusnaw',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        darkTheme: AppTheme.dark(),
        themeMode: ThemeMode.system, // suit le réglage clair/sombre du téléphone
        locale: localeController.locale,
        localizationsDelegates: const [
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: [
          for (final l in supportedTutorLanguages) Locale(l.code),
        ],
        home: const WelcomeScreen(),
      ),
    );
  }
}
