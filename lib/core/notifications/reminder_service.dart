import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

/// Rappel quotidien, programmé sur le téléphone (aucun serveur de push).
/// Ton bienveillant, jamais culpabilisant ; l'élève peut l'arrêter à tout moment.
class ReminderService {
  final _plugin = FlutterLocalNotificationsPlugin();
  bool _ready = false;

  static const _id = 1;
  static const _messages = {
    'en': ('Azul!', 'Five minutes of Kabyle today? Your tutor is here.'),
    'fr': ('Azul !', 'Cinq minutes de kabyle aujourd’hui ? Ton prof t’attend.'),
    'ar': ('أزول!', 'خمس دقائق من القبائلية اليوم؟ أستاذك في انتظارك.'),
    'es': ('¡Azul!', '¿Cinco minutos de cabilio hoy? Tu profesor te espera.'),
    'de': ('Azul!', 'Heute fünf Minuten Kabylisch? Dein Lehrer wartet.'),
  };

  /// Fuseau du téléphone, retrouvé d'après son décalage horaire actuel
  /// (évite un plugin natif). On privilégie quelques fuseaux connus.
  static tz.Location _localLocation() {
    final offset = DateTime.now().timeZoneOffset.inMilliseconds;
    const preferred = [
      'Africa/Algiers', 'Europe/Paris', 'Asia/Shanghai', 'Europe/London',
      'America/Montreal', 'America/New_York', 'Europe/Berlin', 'Europe/Madrid',
    ];
    final now = DateTime.now().millisecondsSinceEpoch;
    bool matches(tz.Location l) => l.timeZone(now).offset == offset;
    for (final name in preferred) {
      final l = tz.getLocation(name);
      if (matches(l)) return l;
    }
    return tz.timeZoneDatabase.locations.values.firstWhere(matches, orElse: () => tz.UTC);
  }

  Future<void> init() async {
    if (_ready || kIsWeb) return;
    try {
      tzdata.initializeTimeZones();
      tz.setLocalLocation(_localLocation());
    } catch (_) {
      // fuseau inconnu : on garde UTC, le rappel sera simplement décalé
    }
    const settings = InitializationSettings(
      android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      iOS: DarwinInitializationSettings(
        requestAlertPermission: false,
        requestBadgePermission: false,
        requestSoundPermission: false,
      ),
    );
    await _plugin.initialize(settings);
    _ready = true;
  }

  /// Demande l'autorisation (Android 13+, iOS). Renvoie false si refusée.
  Future<bool> requestPermission() async {
    await init();
    final android = _plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    if (android != null) {
      return await android.requestNotificationsPermission() ?? false;
    }
    final ios = _plugin.resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>();
    if (ios != null) {
      return await ios.requestPermissions(alert: true, badge: true, sound: true) ?? false;
    }
    return true;
  }

  Future<void> schedule(TimeOfDay time, String lang) async {
    await init();
    await _plugin.cancel(_id);
    final now = tz.TZDateTime.now(tz.local);
    var at = tz.TZDateTime(tz.local, now.year, now.month, now.day, time.hour, time.minute);
    if (!at.isAfter(now)) at = at.add(const Duration(days: 1));
    final (title, body) = _messages[lang] ?? _messages['en']!;
    await _plugin.zonedSchedule(
      _id,
      title,
      body,
      at,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'daily_reminder',
          'Daily reminder',
          channelDescription: 'A gentle daily reminder to practise Kabyle',
          importance: Importance.defaultImportance,
          priority: Priority.defaultPriority,
        ),
        iOS: DarwinNotificationDetails(),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      uiLocalNotificationDateInterpretation: UILocalNotificationDateInterpretation.absoluteTime,
      matchDateTimeComponents: DateTimeComponents.time, // tous les jours à cette heure
    );
  }

  Future<void> cancel() async {
    await init();
    await _plugin.cancel(_id);
  }
}

final reminderService = ReminderService();
