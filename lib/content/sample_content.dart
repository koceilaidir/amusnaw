/// Contenu de démonstration pour les premiers écrans.
/// ⚠️ À faire relire par un linguiste, puis à remplacer par la base kabyle
/// validée servie par le serveur.

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
  });

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

  bool get hasBlank => after.isNotEmpty;
}

class CultureCapsule {
  const CultureCapsule({required this.title, required this.body});
  final String title;
  final String body;
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
}

const yennayer = CultureCapsule(
  title: 'Aseggas ameggaz!',
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
}

const wordOfTheDay = WordOfTheDay('adrar', 'ⴰⴷⵔⴰⵔ', 'mountain');
