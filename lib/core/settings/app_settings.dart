import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Réglages de l'app, enregistrés sur le téléphone.
class AppSettingsState {
  const AppSettingsState({
    this.themeMode = ThemeMode.system,
    this.reminderOn = false,
    this.reminderTime = const TimeOfDay(hour: 19, minute: 0),
    this.accent = 'olivier',
  });

  /// Couleur d'accent choisie dans le menu Thème (id de accentChoices).
  final String accent;

  final ThemeMode themeMode;

  /// Rappel quotidien facultatif (désactivé par défaut : aucune obligation).
  final bool reminderOn;
  final TimeOfDay reminderTime;

  AppSettingsState copyWith({ThemeMode? themeMode, bool? reminderOn, TimeOfDay? reminderTime, String? accent}) =>
      AppSettingsState(
        themeMode: themeMode ?? this.themeMode,
        reminderOn: reminderOn ?? this.reminderOn,
        reminderTime: reminderTime ?? this.reminderTime,
        accent: accent ?? this.accent,
      );
}

class AppSettings extends ValueNotifier<AppSettingsState> {
  AppSettings() : super(const AppSettingsState());

  SharedPreferences? _prefs;

  void load(SharedPreferences prefs) {
    _prefs = prefs;
    value = AppSettingsState(
      themeMode: ThemeMode.values.firstWhere(
        (m) => m.name == prefs.getString('theme_mode'),
        orElse: () => ThemeMode.system,
      ),
      reminderOn: prefs.getBool('reminder_on') ?? false,
      reminderTime: TimeOfDay(
        hour: prefs.getInt('reminder_hour') ?? 19,
        minute: prefs.getInt('reminder_minute') ?? 0,
      ),
      accent: prefs.getString('accent') ?? 'olivier',
    );
  }

  void setThemeMode(ThemeMode m) {
    value = value.copyWith(themeMode: m);
    _prefs?.setString('theme_mode', m.name);
  }

  void setAccent(String id) {
    value = value.copyWith(accent: id);
    _prefs?.setString('accent', id);
  }

  void setReminder({required bool on, TimeOfDay? time}) {
    value = value.copyWith(reminderOn: on, reminderTime: time);
    _prefs?.setBool('reminder_on', on);
    _prefs?.setInt('reminder_hour', value.reminderTime.hour);
    _prefs?.setInt('reminder_minute', value.reminderTime.minute);
  }

  Future<void> reset() async {
    setReminder(on: false);
  }
}

final appSettings = AppSettings();
