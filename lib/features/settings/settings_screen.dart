import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/auth/auth_service.dart';
import '../../core/auth/session.dart';
import '../../core/config.dart';
import '../../core/learning/learner_store.dart';
import '../../core/locale/locale_controller.dart';
import '../../core/notifications/reminder_service.dart';
import '../../core/settings/app_settings.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';
import '../../widgets/dialogs.dart';
import '../onboarding/account_dialog.dart';
import 'privacy_screen.dart';

/// Ouvre les réglages dans une page entière (sur ordinateur comme sur téléphone).
Future<void> openSettings(BuildContext context) => Navigator.of(context, rootNavigator: true).push(
      appRoute((ctx) => Material(
            color: AppPalette.of(ctx).bg,
            child: const ReadingWidth(maxWidth: 720, child: SettingsScreen()),
          )),
    );

/// Réglages : langue du prof, apparence, rappel quotidien, compte, confidentialité.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return AnimatedBuilder(
      animation: Listenable.merge([appSettings, localeController, learnerStore]),
      builder: (context, _) {
        final s = appSettings.value;
        final name = learnerStore.value.name;
        return CustomScrollView(slivers: [
          largeTitleBar(context, 'Réglages'),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 40),
            sliver: SliverList.list(children: [
              if (name.isNotEmpty) ...[
                AppCard(
                  padding: const EdgeInsets.all(16),
                  child: Row(children: [
                    Container(
                      width: 48,
                      height: 48,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(color: p.accentSoft, shape: BoxShape.circle),
                      child: Text(name.substring(0, 1).toUpperCase(),
                          style: TextStyle(fontSize: 19, fontWeight: FontWeight.w600, color: p.accentText)),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(name, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: p.text)),
                        const SizedBox(height: 2),
                        Text('Niveau A1', style: TextStyle(fontSize: 14, color: p.text2)),
                      ]),
                    ),
                  ]),
                ),
                const SizedBox(height: 22),
              ],
              _Section(title: 'Le prof', children: [
                _Row(
                  icon: Icons.translate_rounded,
                  title: 'Explique en',
                  value: localeController.value.label,
                  onTap: () => _pickLanguage(context),
                ),
              ]),
              _Section(title: 'Apparence', children: [
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: _Segments<ThemeMode>(
                    value: s.themeMode,
                    onChanged: appSettings.setThemeMode,
                    options: const {
                      ThemeMode.system: 'Automatique',
                      ThemeMode.light: 'Clair',
                      ThemeMode.dark: 'Sombre',
                    },
                  ),
                ),
              ]),
              if (!kIsWeb) // pas de notification programmée dans un navigateur
                _Section(
                  title: 'Rappel quotidien',
                  footer: 'Facultatif. Un petit signe par jour, tu peux l’ignorer quand tu veux.',
                  children: [
                    _Row(
                      icon: Icons.notifications_none_rounded,
                      title: 'Me le rappeler',
                      trailing: Switch(
                        value: s.reminderOn,
                        activeTrackColor: p.accent,
                        onChanged: (on) => _toggleReminder(context, on),
                      ),
                    ),
                    if (s.reminderOn)
                      _Row(
                        icon: Icons.schedule_rounded,
                        title: 'Heure',
                        value: s.reminderTime.format(context),
                        onTap: () => _pickTime(context),
                      ),
                  ],
                ),
              FutureBuilder<bool>(
                // Sans compte : proposer d'en créer un pour garder sa progression
                future: authService.isGuest(),
                builder: (ctx, g) => g.data == true && authService.googleEnabled
                    ? _Section(
                        title: 'Sans compte',
                        footer: 'Ta progression et tes discussions sont gardées sur ton compte.',
                        children: [
                          _Row(
                            icon: Icons.person_add_alt_rounded,
                            title: 'Créer un compte',
                            onTap: () => showAccountDialog(ctx),
                          ),
                        ],
                      )
                    : const SizedBox.shrink(),
              ),
              _Section(title: 'Compte', children: [
                _Row(
                  icon: Icons.shield_outlined,
                  title: 'Règles de confidentialité',
                  onTap: () => Navigator.of(context).push(appRoute((ctx) => Material(
                        color: AppPalette.of(ctx).bg,
                        child: const ReadingWidth(maxWidth: 720, child: PrivacyScreen()),
                      ))),
                ),
                _Row(icon: Icons.logout_rounded, title: 'Se déconnecter', onTap: () => _signOut(context)),
                _Row(
                  icon: Icons.delete_outline_rounded,
                  title: 'Supprimer mon compte',
                  danger: true,
                  onTap: () => _deleteAccount(context),
                ),
              ]),
              Center(
                child: Text('Amusnaw · ${AppConfig.aiName}', style: TextStyle(fontSize: 13, color: p.text2)),
              ),
            ]),
          ),
        ]);
      },
    );
  }

  Future<void> _pickLanguage(BuildContext context) async {
    final l = await showChoice<TutorLanguage>(
      context,
      'Ton prof explique en',
      {for (final l in supportedTutorLanguages) l: l.label},
      selected: localeController.value,
    );
    if (l == null) return;
    localeController.choose(l, syncServer: true);
    final s = appSettings.value;
    if (s.reminderOn) reminderService.schedule(s.reminderTime, l.code);
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
        await showInfo(context, 'Notifications désactivées',
            'Autorise les notifications d’Amusnaw dans les réglages du téléphone pour recevoir le rappel.');
      }
      return;
    }
    appSettings.setReminder(on: true);
    await reminderService.schedule(appSettings.value.reminderTime, localeController.value.code);
  }

  Future<void> _pickTime(BuildContext context) async {
    final picked = await showTimePicker(context: context, initialTime: appSettings.value.reminderTime);
    if (picked == null) return;
    appSettings.setReminder(on: true, time: picked);
    await reminderService.schedule(picked, localeController.value.code);
  }

  Future<void> _signOut(BuildContext context) async {
    final yes = await showConfirm(context, 'Se déconnecter ?',
        'Ta progression reste enregistrée sur le serveur. Reconnecte-toi pour continuer.', 'Se déconnecter');
    if (yes && context.mounted) await endSession(context);
  }

  Future<void> _deleteAccount(BuildContext context) async {
    final yes = await showConfirm(
      context,
      'Supprimer ton compte ?',
      'Tes conversations, tes mots appris et ta progression seront effacés définitivement.',
      'Supprimer',
      danger: true,
    );
    if (!yes || !context.mounted) return;
    try {
      await api.delete('/me');
      if (context.mounted) await endSession(context);
    } catch (_) {
      if (context.mounted) {
        await showInfo(context, 'Suppression impossible', 'Le serveur est injoignable. Réessaie plus tard.');
      }
    }
  }
}

/// Un groupe de réglages : petit titre, carte, note facultative.
class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children, this.footer});
  final String title;
  final String? footer;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final rows = <Widget>[];
    for (var i = 0; i < children.length; i++) {
      if (i > 0) rows.add(Divider(height: 1, thickness: .5, indent: 56, color: p.separator));
      rows.add(children[i]);
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 22),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(padding: const EdgeInsets.fromLTRB(6, 0, 6, 8), child: Caption(title)),
        AppCard(padding: const EdgeInsets.symmetric(vertical: 4), child: Column(children: rows)),
        if (footer != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(6, 8, 6, 0),
            child: Text(footer!, style: TextStyle(fontSize: 13, height: 1.4, color: p.text2)),
          ),
      ]),
    );
  }
}

/// Une ligne de réglage : icône, titre, valeur, flèche (ou interrupteur).
class _Row extends StatelessWidget {
  const _Row({required this.icon, required this.title, this.value, this.trailing, this.onTap, this.danger = false});
  final IconData icon;
  final String title;
  final String? value;
  final Widget? trailing;
  final VoidCallback? onTap;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    final color = danger ? const Color(0xFFB3261E) : p.text;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      hoverColor: p.fill.withValues(alpha: .6),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 54),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          child: Row(children: [
            Container(
              width: 30,
              height: 30,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: danger ? const Color(0x1AB3261E) : p.accentSoft,
                borderRadius: BorderRadius.circular(9),
              ),
              child: Icon(icon, size: 18, color: danger ? color : p.accentText),
            ),
            const SizedBox(width: 12),
            Expanded(child: Text(title, style: TextStyle(fontSize: 16, color: color))),
            if (value != null) Text(value!, style: TextStyle(fontSize: 15, color: p.text2)),
            if (trailing != null)
              trailing!
            else if (onTap != null && !danger) ...[
              const SizedBox(width: 6),
              Icon(Icons.chevron_right_rounded, size: 22, color: p.text2),
            ],
          ]),
        ),
      ),
    );
  }
}

/// Choix entre quelques options, sur une seule ligne.
class _Segments<T> extends StatelessWidget {
  const _Segments({required this.value, required this.onChanged, required this.options});
  final T value;
  final ValueChanged<T> onChanged;
  final Map<T, String> options;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: p.fill, borderRadius: BorderRadius.circular(14)),
      child: Row(children: [
        for (final e in options.entries)
          Expanded(
            child: GestureDetector(
              onTap: () => onChanged(e.key),
              child: MouseRegion(
                cursor: SystemMouseCursors.click,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 150),
                  height: 40,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: e.key == value ? p.surface : Colors.transparent,
                    borderRadius: BorderRadius.circular(11),
                    boxShadow: e.key == value ? p.shadow : null,
                  ),
                  child: Text(e.value,
                      style: TextStyle(
                          fontSize: 15,
                          fontWeight: e.key == value ? FontWeight.w600 : FontWeight.w400,
                          color: e.key == value ? p.text : p.text2)),
                ),
              ),
            ),
          ),
      ]),
    );
  }
}
