/// Modèles de contenu (leçons, exercices, capsules) + contenu de secours
/// utilisé seulement si le serveur est injoignable. Le vrai contenu vient
/// du serveur (/content/...), modifiable sans republier l'app.

class ChoiceExercise {
  const ChoiceExercise({
    required this.id,
    required this.instruction,
    required this.before,
    this.after = '',
    required this.options,
    required this.answer,
    this.translation,
    required this.explanation,
    this.tifinagh,
  });

  factory ChoiceExercise.fromJson(Map<String, dynamic> j) => ChoiceExercise(
        id: j['id'] as String,
        instruction: (j['instruction'] as String?) ?? 'WHAT DOES IT MEAN?',
        before: j['before'] as String,
        after: (j['after'] as String?) ?? '',
        options: (j['options'] as List).cast<String>(),
        answer: j['answer'] as String,
        translation: j['translation'] as String?,
        explanation: (j['explanation'] as String?) ?? '',
        tifinagh: j['tifinagh'] as String?,
      );

  final String id;

  /// Consigne courte (« COMPLETE THE GREETING »).
  final String instruction;

  /// Texte avant le blanc (ou le mot seul pour une question de sens).
  final String before;

  /// Texte après le blanc. Vide = pas de blanc, on affiche [before] seul.
  final String after;
  final List<String> options;
  final String answer;
  final String? translation;
  final String explanation;

  /// Écriture tifinagh du mot (affichée en petit sous le mot).
  final String? tifinagh;

  bool get hasBlank => after.isNotEmpty;
}

class CultureCapsule {
  const CultureCapsule({required this.title, required this.body, this.kab = ''});
  final String title;
  final String body;

  /// Titre ou expression en kabyle (« Aseggas ameggaz! »), peut être vide.
  final String kab;

  factory CultureCapsule.fromJson(Map<String, dynamic> j) => CultureCapsule(
        title: j['title'] as String,
        body: j['body'] as String,
        kab: (j['kab'] as String?) ?? '',
      );
}

class Lesson {
  const Lesson({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.exercises,
    this.capsule,
  });
  final String id;
  final String title;
  final String subtitle;
  final List<ChoiceExercise> exercises;
  final CultureCapsule? capsule;

  factory Lesson.fromJson(Map<String, dynamic> j) => Lesson(
        id: j['id'] as String,
        title: j['title'] as String,
        subtitle: (j['subtitle'] as String?) ?? '',
        exercises: ((j['exercises'] as List?) ?? const [])
            .map((e) => ChoiceExercise.fromJson(e as Map<String, dynamic>))
            .toList(),
        capsule: j['capsule_data'] is Map<String, dynamic>
            ? CultureCapsule.fromJson(j['capsule_data'] as Map<String, dynamic>)
            : null,
      );
}

/// Résumé d'une leçon pour la liste (sans les exercices).
class LessonSummary {
  const LessonSummary({required this.id, required this.title, required this.subtitle,
      this.level = 'A1', this.count = 0});
  final String id, title, subtitle, level;
  final int count;

  factory LessonSummary.fromJson(Map<String, dynamic> j) => LessonSummary(
        id: j['id'] as String,
        title: j['title'] as String,
        subtitle: (j['subtitle'] as String?) ?? '',
        level: (j['level'] as String?) ?? 'A1',
        count: (j['count'] as num?)?.toInt() ?? 0,
      );
}

const yennayer = CultureCapsule(
  kab: 'Aseggas ameggaz!',
  title: 'Yennayer',
  body: '“Happy new year!” — wished on Yennayer, 12 January, when the Amazigh '
      'calendar turns. Families share a festive meal to bless the year ahead.',
);

const firstWords = Lesson(
  id: 'a1-first-words',
  title: "At grandmother's table",
  subtitle: 'Greetings, water and bread',
  capsule: yennayer,
  exercises: [
    ChoiceExercise(
      id: 'amek-tellid',
      instruction: 'COMPLETE THE GREETING',
      before: 'Azul! Amek ',
      after: '?',
      options: ['tellid', 'aman', 'adrar'],
      answer: 'tellid',
      translation: 'Hello! How are you? (to a man)',
      explanation: "Kabyle changes the verb for who you speak to. To a woman, you'd say Amek tellam?",
    ),
    ChoiceExercise(
      id: 'aman',
      instruction: 'WHAT DOES IT MEAN?',
      before: 'aman',
      options: ['water', 'bread', 'house'],
      answer: 'water',
      explanation: 'Aman is water — one of the first words children hear at the table.',
    ),
    ChoiceExercise(
      id: 'aghrum',
      instruction: 'WHAT DOES IT MEAN?',
      before: 'aɣrum',
      options: ['mountain', 'bread', 'water'],
      answer: 'bread',
      explanation: 'Aɣrum is bread. The letter ɣ sounds like a French r, from the throat.',
    ),
    ChoiceExercise(
      id: 'tanemmirt',
      instruction: 'WHAT DOES IT MEAN?',
      before: 'Tanemmirt',
      options: ['Goodbye', 'Thank you', 'Hello'],
      answer: 'Thank you',
      explanation: 'Tanemmirt — thank you. Use it generously, it opens every door.',
    ),
    ChoiceExercise(
      id: 'axxam',
      instruction: 'WHAT DOES IT MEAN?',
      before: 'axxam',
      options: ['house', 'friend', 'sun'],
      answer: 'house',
      explanation: 'Axxam is the house — and the family who lives in it.',
    ),
  ],
);

/// Parcours A1 affiché dans l'onglet Learn.
const a1Lessons = [
  firstWords,
  Lesson(id: 'a1-family', title: 'The family', subtitle: 'Yemma, baba and the others', exercises: []),
  Lesson(id: 'a1-numbers', title: 'Numbers', subtitle: 'Counting at the market', exercises: []),
  Lesson(id: 'a1-village', title: 'The village', subtitle: 'Axxam, tajmaɛt, the fountain', exercises: []),
];

class WordOfTheDay {
  const WordOfTheDay(this.word, this.tifinagh, this.meaning);
  final String word, tifinagh, meaning;

  factory WordOfTheDay.fromJson(Map<String, dynamic> j) => WordOfTheDay(
        j['kab'] as String,
        (j['tifinagh'] as String?) ?? '',
        j['fr'] as String,
      );
}

const wordOfTheDay = WordOfTheDay('adrar', 'ⴰⴷⵔⴰⵔ', 'mountain');
