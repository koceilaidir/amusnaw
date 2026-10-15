import '../../content/sample_content.dart';
import '../api/api_client.dart';

/// Ce que l'écran « Today » affiche, servi par le serveur.
class TodayContent {
  const TodayContent({this.word, this.capsule, this.lessonId, this.lessonTitle, this.lessonSubtitle});
  final WordOfTheDay? word;
  final CultureCapsule? capsule;
  final String? lessonId;
  final String? lessonTitle;
  final String? lessonSubtitle;

  /// Contenu de secours si le serveur est injoignable.
  static const fallback = TodayContent(
    word: wordOfTheDay,
    capsule: yennayer,
    lessonId: 'a1-first-words',
    lessonTitle: "At grandmother's table",
    lessonSubtitle: 'Greetings, water and bread',
  );
}

/// Accès aux contenus du serveur (leçons, mot du jour, capsules), avec un
/// petit cache mémoire et un repli local hors connexion.
class ContentRepository {
  TodayContent? _today;
  List<LessonSummary>? _lessons;
  final _lessonCache = <String, Lesson>{};

  void clear() {
    _today = null;
    _lessons = null;
    _lessonCache.clear();
  }

  Future<TodayContent> today({bool refresh = false}) async {
    if (_today != null && !refresh) return _today!;
    try {
      final offset = DateTime.now().timeZoneOffset.inMinutes;
      final j = await api.get('/content/today?tz_offset_minutes=$offset');
      final lesson = j['lesson'] as Map<String, dynamic>?;
      _today = TodayContent(
        word: j['word'] is Map<String, dynamic>
            ? WordOfTheDay.fromJson(j['word'] as Map<String, dynamic>)
            : null,
        capsule: j['capsule'] is Map<String, dynamic>
            ? CultureCapsule.fromJson(j['capsule'] as Map<String, dynamic>)
            : null,
        lessonId: lesson?['id'] as String?,
        lessonTitle: lesson?['title'] as String?,
        lessonSubtitle: lesson?['subtitle'] as String?,
      );
    } catch (_) {
      _today ??= TodayContent.fallback;
    }
    return _today!;
  }

  Future<List<LessonSummary>> lessons({bool refresh = false}) async {
    if (_lessons != null && !refresh) return _lessons!;
    try {
      final list = await api.getAny('/content/lessons') as List;
      _lessons = list.map((e) => LessonSummary.fromJson(e as Map<String, dynamic>)).toList();
    } catch (_) {
      _lessons ??= [
        for (final l in a1Lessons)
          LessonSummary(id: l.id, title: l.title, subtitle: l.subtitle, count: l.exercises.length),
      ];
    }
    return _lessons!;
  }

  Future<Lesson> lesson(String id) async {
    if (_lessonCache[id] != null) return _lessonCache[id]!;
    try {
      final l = Lesson.fromJson(await api.get('/content/lessons/$id'));
      return _lessonCache[id] = l;
    } catch (_) {
      return a1Lessons.firstWhere((l) => l.id == id, orElse: () => firstWords);
    }
  }
}

final contentRepository = ContentRepository();
