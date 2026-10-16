import 'package:flutter/cupertino.dart';

import '../../content/sample_content.dart';
import '../../core/content/content_repository.dart';
import '../../widgets/common.dart';
import '../../widgets/content_cards.dart';

/// Capsules de culture et d'histoire, servies par le serveur.
class CultureScreen extends StatefulWidget {
  const CultureScreen({super.key});

  @override
  State<CultureScreen> createState() => _CultureScreenState();
}

class _CultureScreenState extends State<CultureScreen> {
  late final Future<List<CultureCapsule>> _capsules = contentRepository.capsules();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<CultureCapsule>>(
      future: _capsules,
      builder: (context, snap) => CustomScrollView(
        slivers: [
          largeTitleBar(context, 'Culture et histoire'),
          if (snap.data == null)
            const SliverToBoxAdapter(
              child: Padding(padding: EdgeInsets.all(32), child: CupertinoActivityIndicator()),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              sliver: SliverList.separated(
                itemCount: snap.data!.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (_, i) => CapsuleCard(capsule: snap.data![i], showBody: true),
              ),
            ),
        ],
      ),
    );
  }
}
