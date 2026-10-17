import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/session.dart';
import '../../core/config.dart';
import '../../core/learning/learner_store.dart';
import '../../core/locale/locale_controller.dart';
import '../../core/notifications/reminder_service.dart';
import '../../core/settings/app_settings.dart';
import '../../theme/app_theme.dart';
import '../../theme/mark.dart';
import '../../widgets/common.dart';

/// Réglages : langue du prof, apparence, rappel quotidien, confidentialité,
/// déconnexion et suppression du compte.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Material(
      color: p.bg,
      child: CupertinoPageScaffold(
        backgroundColor: p.bg,
        child: AnimatedBuilder(
          animation: Listenable.merge([appSettings, localeController, learnerStore]),
          builder: (context, _) {
            final s = appSettings.value;
            final name = learnerStore.value.name;
            return CustomScrollView(
              slivers: [
                largeTitleBar(context, 'Réglages'),
                SliverToBoxAdapter(
                  child: Column(children: [
                    const SizedBox(height: 8),
                    AmusnawMark(size: 52, color: p.text),
                    const SizedBox(height: 8),
                    if (name.isNotEmpty)
                      Text(name, style: AppTheme.serif(size: 22, color: p.text)),
                    CupertinoListSection.insetGrouped(
                      backgroundColor: p.bg,
                      header: const Text('LE PROF'),
                      children: [
                        CupertinoListTile(
                          leading: const TintIcon(CupertinoIcons.globe),
                          title: Text('Explique en', style: TextStyle(color: p.text)),
                          additionalInfo: Text(localeController.value.label),
                          trailing: const CupertinoListTileChevron(),
                          onTap: () => _pickLanguage(context),
                        ),
                      ],
                    ),
                    CupertinoListSection.insetGrouped(
                      backgroundColor: p.bg,
                      header: const Text('APPARENCE'),
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(12),
                          child: SizedBox(
                            width: double.infinity,
                            child: CupertinoSlidingSegmentedControl<ThemeMode>(
                              groupValue: s.themeMode,
                              onValueChanged: (m) {
                                if (m != null) appSettings.setThemeMode(m);
                              },
                              children: const {
                                ThemeMode.system: Text('Automatique'),
                                ThemeMode.light: Text('Clair'),
                                ThemeMode.dark: Text('Sombre'),
                              },
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (!kIsWeb) // pas de notification programmée dans un navigateur
                    CupertinoListSection.insetGrouped(
                      backgroundColor: p.bg,
                      header: const Text('RAPPEL QUOTIDIEN'),
                      footer: const Text('Facultatif. Un petit signe par jour — tu peux l’ignorer quand tu veux.'),
                      children: [
                        CupertinoListTile(
                          leading: const TintIcon(CupertinoIcons.bell_fill),
                          title: Text('Me le rappeler', style: TextStyle(color: p.text)),
                          trailing: CupertinoSwitch(
                            value: s.reminderOn,
                            activeTrackColor: p.ink,
                            onChanged: (on) => _toggleReminder(context, on),
                          ),
                        ),
                        if (s.reminderOn)
                          CupertinoListTile(
                            leading: const TintIcon(CupertinoIcons.clock_fill),
                            title: Text('Heure', style: TextStyle(color: p.text)),
                            additionalInfo: Text(s.reminderTime.format(context)),
                            trailing: const CupertinoListTileChevron(),
                            onTap: () => _pickTime(context),
                          ),
                      ],
                    ),
                    CupertinoListSection.insetGrouped(
                      backgroundColor: p.bg,
                      header: const Text('COMPTE'),
                      children: [
                        CupertinoListTile(
                          leading: const TintIcon(CupertinoIcons.lock_shield_fill),
                          title: Text('Confidentialité', style: TextStyle(color: p.text)),
                          trailing: const CupertinoListTileChevron(),
                          onTap: () => launchUrl(Uri.parse('${AppConfig.apiBaseUrl}/privacy'),
                              mode: LaunchMode.inAppBrowserView),
                        ),
                        CupertinoListTile(
                          leading: const TintIcon(CupertinoIcons.square_arrow_right),
                          title: Text('Se déconnecter', style: TextStyle(color: p.text)),
                          onTap: () => _signOut(context),
                        ),
                        CupertinoListTile(
                          leading: const TintIcon(CupertinoIcons.trash_fill),
                          title: const Text('Supprimer mon compte',
                              style: TextStyle(color: CupertinoColors.destructiveRed)),
                          onTap: () => _deleteAccount(context),
                        ),
                      ],
                    ),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(24, 4, 24, 32),
                      child: Text('Amusnaw · réalisé pour le HCA',
                          style: TextStyle(fontSize: 13, color: p.text2)),
                    ),
                  ]),
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  void _pickLanguage(BuildContext context) {
    showCupertinoModalPopup<void>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        title: const Text('Ton prof explique en'),
        actions: [
          for (final l in supportedTutorLanguages)
            CupertinoActionSheetAction(
              isDefaultAction: l.code == localeController.value.code,
              onPressed: () {
                localeController.choose(l, syncServer: true);
                final s = appSettings.value;
                if (s.reminderOn) reminderService.schedule(s.reminderTime, l.code);
                Navigator.pop(ctx);
              },
              child: Text(l.label),
            ),
        ],
        cancelButton: CupertinoActionSheetAction(
          onPressed: () => Navigator.pop(ctx),
          child: const Text('Annuler'),
        ),
      ),
    );
  }

  Future<void> _toggleReminder(BuildContext context, bool on) async {
    if (!on) {
      appSettings.setReminder(on: false);
      await reminderService.cancel();
      return;
    }
    final granted = await reminderService.requestPermission();
    if (!granted) {
      if (context.mounted) {
        _alert(context, 'Notifications désactivées',
            'Autorise les notifications d’Amusnaw dans les réglages du téléphone pour recevoir le rappel.');
      }
      return;
    }
    appSettings.setReminder(on: true);
    await reminderService.schedule(appSettings.value.reminderTime, localeController.value.code);
  }

  Future<void> _pickTime(BuildContext context) async {
    var picked = appSettings.value.reminderTime;
    final now = DateTime.now();
    final ok = await showCupertinoModalPopup<bool>(
      context: context,
      builder: (ctx) => Container(
        height: 300,
        color: AppPalette.of(ctx).surface,
        child: SafeArea(
          top: false,
          child: Column(children: [
            Align(
              alignment: Alignment.centerRight,
              child: CupertinoButton(
                child: const Text('OK'),
                onPressed: () => Navigator.pop(ctx, true),
              ),
            ),
            Expanded(
              child: CupertinoDatePicker(
                mode: CupertinoDatePickerMode.time,
                initialDateTime: DateTime(now.year, now.month, now.day, picked.hour, picked.minute),
                onDateTimeChanged: (d) => picked = TimeOfDay(hour: d.hour, minute: d.minute),
              ),
            ),
          ]),
        ),
      ),
    );
    if (ok != true) return;
    appSettings.setReminder(on: true, time: picked);
    await reminderService.schedule(picked, localeController.value.code);
  }

  Future<void> _signOut(BuildContext context) async {
    final yes = await _confirm(context, 'Se déconnecter ?',
        'Ta progression reste enregistrée sur le serveur. Reconnecte-toi pour continuer.', 'Se déconnecter');
    if (yes && context.mounted) await endSession(context);
  }

  Future<void> _deleteAccount(BuildContext context) async {
    final yes = await _confirm(
      context,
      'Supprimer ton compte ?',
      'Tes conversations, tes mots appris et ta progression seront effacés définitivement.',
      'Supprimer',
    );
    if (!yes || !context.mounted) return;
    try {
      await api.delete('/me');
      if (context.mounted) await endSession(context);
    } catch (_) {
      if (context.mounted) {
        _alert(context, 'Suppression impossible', 'Le serveur est injoignable. Réessaie plus tard.');
      }
    }
  }

  Future<bool> _confirm(BuildContext context, String title, String body, String action) async {
    final r = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          CupertinoDialogAction(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(action),
          ),
        ],
      ),
    );
    return r ?? false;
  }

  void _alert(BuildContext context, String title, String body) {
    showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          CupertinoDialogAction(onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
        ],
      ),
    );
  }
}
