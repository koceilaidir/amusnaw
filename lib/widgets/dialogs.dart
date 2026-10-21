import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Fenêtres de l'app, au style du site (et non celles d'iOS) : coins arrondis,
/// titre, texte, puis les boutons à droite.

/// Page sans animation de glissement (le contenu change sur place, comme un site).
Route<T> appRoute<T>(WidgetBuilder builder) => PageRouteBuilder<T>(
      pageBuilder: (context, _, __) => builder(context),
      transitionDuration: Duration.zero,
      reverseTransitionDuration: Duration.zero,
    );

class _AppDialog extends StatelessWidget {
  const _AppDialog({required this.title, this.body, this.content, required this.actions});
  final String title;
  final String? body;
  final Widget? content;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return Dialog(
      backgroundColor: p.surface,
      surfaceTintColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(24),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(title,
                style: TextStyle(fontSize: 21, fontWeight: FontWeight.w600, letterSpacing: -.3, color: p.text)),
            if (body != null) ...[
              const SizedBox(height: 10),
              Text(body!, style: TextStyle(fontSize: 15, height: 1.45, color: p.text2)),
            ],
            if (content != null) ...[const SizedBox(height: 16), content!],
            const SizedBox(height: 22),
            Wrap(alignment: WrapAlignment.end, spacing: 8, runSpacing: 8, children: actions),
          ]),
        ),
      ),
    );
  }
}

ButtonStyle _primary(AppPalette p, {bool danger = false}) => FilledButton.styleFrom(
      backgroundColor: danger ? const Color(0xFFB3261E) : p.accent,
      foregroundColor: danger ? Colors.white : p.onAccent,
      minimumSize: const Size(0, 44),
      padding: const EdgeInsets.symmetric(horizontal: 20),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      textStyle: const TextStyle(fontFamily: AppTheme.font, fontSize: 15, fontWeight: FontWeight.w600),
    );

ButtonStyle _secondary(AppPalette p) => TextButton.styleFrom(
      foregroundColor: p.text,
      minimumSize: const Size(0, 44),
      padding: const EdgeInsets.symmetric(horizontal: 18),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      textStyle: const TextStyle(fontFamily: AppTheme.font, fontSize: 15, fontWeight: FontWeight.w500),
    );

/// Information simple, un bouton « OK ».
Future<void> showInfo(BuildContext context, String title, String body) {
  final p = AppPalette.of(context);
  return showDialog<void>(
    context: context,
    builder: (ctx) => _AppDialog(title: title, body: body, actions: [
      FilledButton(style: _primary(p), onPressed: () => Navigator.pop(ctx), child: const Text('OK')),
    ]),
  );
}

/// Confirmation : vrai si l'élève choisit l'action.
Future<bool> showConfirm(BuildContext context, String title, String body, String action,
    {bool danger = false}) async {
  final p = AppPalette.of(context);
  final r = await showDialog<bool>(
    context: context,
    builder: (ctx) => _AppDialog(title: title, body: body, actions: [
      TextButton(style: _secondary(p), onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
      FilledButton(style: _primary(p, danger: danger), onPressed: () => Navigator.pop(ctx, true), child: Text(action)),
    ]),
  );
  return r ?? false;
}

/// Un ou deux champs à remplir ; renvoie les valeurs, ou null si annulé.
Future<List<String>?> showFields(BuildContext context, String title, String? message,
    List<(String, TextInputType)> fields,
    {String action = 'Continuer'}) {
  final p = AppPalette.of(context);
  final ctrls = [for (final _ in fields) TextEditingController()];
  return showDialog<List<String>>(
    context: context,
    builder: (ctx) {
      void ok() => Navigator.pop(ctx, [for (final c in ctrls) c.text.trim()]);
      return _AppDialog(
        title: title,
        body: message,
        content: Column(children: [
          for (var i = 0; i < fields.length; i++)
            Padding(
              padding: EdgeInsets.only(top: i == 0 ? 0 : 10),
              child: TextField(
                controller: ctrls[i],
                keyboardType: fields[i].$2,
                autofocus: i == 0,
                autocorrect: false,
                textInputAction: i == fields.length - 1 ? TextInputAction.done : TextInputAction.next,
                onSubmitted: i == fields.length - 1 ? (_) => ok() : null,
                style: TextStyle(fontSize: 16, color: p.text),
                cursorColor: p.accent,
                decoration: InputDecoration(
                  hintText: fields[i].$1,
                  hintStyle: TextStyle(color: p.text2),
                  filled: true,
                  fillColor: p.fill,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                  focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: p.accent)),
                ),
              ),
            ),
        ]),
        actions: [
          TextButton(style: _secondary(p), onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
          FilledButton(style: _primary(p), onPressed: ok, child: Text(action)),
        ],
      );
    },
  );
}

/// Choix dans une liste (langue…) ; renvoie la valeur choisie, ou null.
Future<T?> showChoice<T>(BuildContext context, String title, Map<T, String> options, {T? selected}) {
  final p = AppPalette.of(context);
  return showDialog<T>(
    context: context,
    builder: (ctx) => _AppDialog(
      title: title,
      content: Column(children: [
        for (final e in options.entries)
          Material(
            color: e.key == selected ? p.fill : Colors.transparent,
            borderRadius: BorderRadius.circular(14),
            child: InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: () => Navigator.pop(ctx, e.key),
              child: Container(
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: Row(children: [
                  Expanded(child: Text(e.value, style: TextStyle(fontSize: 16, color: p.text))),
                  if (e.key == selected) Icon(Icons.check_rounded, size: 20, color: p.accent),
                ]),
              ),
            ),
          ),
      ]),
      actions: [
        TextButton(style: _secondary(p), onPressed: () => Navigator.pop(ctx), child: const Text('Annuler')),
      ],
    ),
  );
}
