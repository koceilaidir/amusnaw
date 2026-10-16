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
        instruction: (j['instruction'] as String?) ?? 'QUE VEUT DIRE CE MOT ?',
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
  body: '« Bonne année ! » — le 12 janvier, on fête Yennayer, le nouvel an amazigh. '
      'Les familles partagent un repas de fête pour bénir l’année qui commence.',
);

const firstWords = Lesson(
  id: 'a1-first-words',
  title: 'À la table de grand-mère',
  subtitle: 'Saluer, l’eau et le pain',
  capsule: yennayer,
  exercises: [
    ChoiceExercise(
      id: 'amek-tellid',
      instruction: 'COMPLÈTE LA SALUTATION',
      before: 'Azul! Amek ',
      after: '?',
      options: ['tellid', 'aman', 'adrar'],
      answer: 'tellid',
      translation: 'Bonjour ! Comment vas-tu ?',
      explanation: 'Amek tellid ? — comment vas-tu ? C’est la question qu’on pose juste après Azul.',
    ),
    ChoiceExercise(
      id: 'aman',
      instruction: 'QUE VEUT DIRE CE MOT ?',
      before: 'aman',
      options: ['l’eau', 'le pain', 'la maison'],
      answer: 'l’eau',
      explanation: 'Aman, c’est l’eau — un des premiers mots qu’on entend à table.',
    ),
    ChoiceExercise(
      id: 'aghrum',
      instruction: 'QUE VEUT DIRE CE MOT ?',
      before: 'aɣrum',
      options: ['la montagne', 'le pain', 'l’eau'],
      answer: 'le pain',
      explanation: 'Aɣrum, c’est le pain. Le ɣ se prononce au fond de la gorge, comme un r français.',
    ),
    ChoiceExercise(
      id: 'tanemmirt',
      instruction: 'QUE VEUT DIRE CE MOT ?',
      before: 'Tanemmirt',
      options: ['au revoir', 'merci', 'bonjour'],
      answer: 'merci',
      explanation: 'Tanemmirt — merci. À utiliser sans compter.',
    ),
    ChoiceExercise(
      id: 'axxam',
      instruction: 'QUE VEUT DIRE CE MOT ?',
      before: 'axxam',
      options: ['la maison', 'l’ami', 'le soleil'],
      answer: 'la maison',
      explanation: 'Axxam, c’est la maison — et aussi la famille qui y vit.',
    ),
  ],
);

/// Parcours A1 affiché dans l'onglet Learn.
const a1Lessons = [
  firstWords,
  Lesson(id: 'a1-family', title: 'La famille', subtitle: 'Yemma, baba et les autres', exercises: []),
  Lesson(id: 'a1-numbers', title: 'Les nombres', subtitle: 'Compter au marché', exercises: []),
  Lesson(id: 'a1-village', title: 'Le village', subtitle: 'Axxam, tajmaɛt, la fontaine', exercises: []),
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

const wordOfTheDay = WordOfTheDay('adrar', 'ⴰⴷⵔⴰⵔ', 'la montagne');
