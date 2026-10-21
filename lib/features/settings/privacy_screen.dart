import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../core/config.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common.dart';

/// Règles de confidentialité, affichées dans l'app (même onglet, même design).
/// Le texte vient du serveur (/privacy) : une seule version à tenir à jour.
class PrivacyScreen extends StatefulWidget {
  const PrivacyScreen({super.key});

  @override
  State<PrivacyScreen> createState() => _PrivacyScreenState();
}

class _Part {
  const _Part(this.title, this.paragraphs);
  final String title;
  final List<String> paragraphs;
}

class _PrivacyScreenState extends State<PrivacyScreen> {
  late final Future<(String, List<_Part>)?> _page = _load();

  static String _text(String html) => html
      .replaceAll(RegExp(r'<br\s*/?>'), '\n')
      .replaceAll(RegExp(r'<[^>]+>'), '')
      .replaceAll('&nbsp;', ' ')
      .replaceAll('&amp;', '&')
      .replaceAll('&rarr;', '→')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  Future<(String, List<_Part>)?> _load() async {
    try {
      final res = await http
          .get(Uri.parse('${AppConfig.apiBaseUrl}/privacy'))
          .timeout(const Duration(seconds: 15));
      if (res.statusCode != 200) return null;
      final html = res.body;
      final main = RegExp(r'<main>([\s\S]*?)</main>').firstMatch(html)?.group(1) ?? html;
      final lead = RegExp(r'<p class="lead">([\s\S]*?)</p>').firstMatch(main)?.group(1) ?? '';
      final parts = <_Part>[];
      for (final m in RegExp(r'<h2>([\s\S]*?)</h2>([\s\S]*?)(?=<h2>|<a class="back"|$)').allMatches(main)) {
        final ps = RegExp(r'<p>([\s\S]*?)</p>').allMatches(m.group(2)!).map((x) => _text(x.group(1)!)).toList();
        parts.add(_Part(_text(m.group(1)!), ps));
      }
      return (_text(lead), parts);
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = AppPalette.of(context);
    return FutureBuilder<(String, List<_Part>)?>(
      future: _page,
      builder: (context, snap) {
        final done = snap.connectionState == ConnectionState.done;
        final page = snap.data;
        return CustomScrollView(slivers: [
          largeTitleBar(context, 'Confidentialité'),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 40),
            sliver: SliverList.list(children: [
              if (!done)
                const Padding(padding: EdgeInsets.all(32), child: Center(child: Spinner()))
              else if (page == null)
                Text('Impossible de charger les règles pour le moment. Vérifie ta connexion et réessaie.',
                    style: TextStyle(fontSize: 16, height: 1.5, color: p.text2))
              else ...[
                if (page.$1.isNotEmpty) ...[
                  Text(page.$1, style: TextStyle(fontSize: 17, height: 1.5, color: p.text2)),
                  const SizedBox(height: 22),
                ],
                for (final part in page.$2) ...[
                  Padding(padding: const EdgeInsets.fromLTRB(6, 0, 6, 8), child: Caption(part.title)),
                  AppCard(
                    padding: const EdgeInsets.fromLTRB(18, 16, 18, 4),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      for (final t in part.paragraphs)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Text(t, style: TextStyle(fontSize: 15.5, height: 1.55, color: p.text)),
                        ),
                    ]),
                  ),
                  const SizedBox(height: 22),
                ],
              ],
            ]),
          ),
        ]);
      },
    );
  }
}
