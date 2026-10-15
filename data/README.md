# Données kabyles d'Amusnaw

Tout ce dossier est **généré** par les scripts de `data_pipeline/` à partir des livres fournis. Chaque ligne porte `needs_review: true` : rien n'est considéré comme validé tant qu'un linguiste ne l'a pas relu.

Les livres sources sont des publications du HCA, utilisées **avec l'autorisation du HCA** pour le projet Amusnaw (base du prof, contenus de l'app, entraînement d'amusnaw-v1). Le dossier reste exclu de Git : il ne doit pas être publié hors du projet.

| Fichier | Contenu | Usage |
|---|---|---|
| `lexicon.jsonl` | Mots kabyle ↔ français du lexique des animaux marins (fiches, index, glossaire) | dictionnaire du prof, exercices de vocabulaire |
| `glossaries.jsonl` | Glossaires de fin de *Mmis n igellil* et *Ageldun amecṭuḥ* (néologismes) | dictionnaire |
| `sentences.jsonl` | Phrases kabyles authentiques (descriptions du lexique marin) | exemples, lecture, pré-entraînement |
| `parallel_petit_prince.jsonl` | *Le Petit Prince* ↔ *Ageldun amecṭuḥ*, phrase par phrase | traduction, exercices, entraînement |
| `parallel_camus.jsonl` | Camus, *Misère de la Kabylie* (+ discours du Nobel) ↔ *Lḥif n tmurt n Leqbayel* | idem |
| `parallel_feraoun.jsonl` | *Le fils du pauvre* (partie II) ↔ *Mmis n igellil* | idem |
| `feraoun_kab.txt`, `petit_prince_kab.txt`, `camus_kab.txt`, `book2_text.txt` | Textes kabyles complets, convertis en Unicode | lecture, recherche, pré-entraînement |

Champs des paires parallèles : `fr`, `kab`, `chapter`, `bead` (ex. `[1, 2]` = 1 phrase FR pour 2 phrases KAB), `cost` (plus bas = plus sûr), `confident` (estimation automatique : à relire en priorité les `false`).

## Regénérer

```bash
cd data_pipeline
pip install pymupdf pyspellchecker
python extract_amawal_iselman.py livre_2.pdf ../data
python extract_kabyle_pdf.py livre_3.pdf ../data/feraoun_kab.txt
python extract_kabyle_pdf.py livre_4.pdf ../data/petit_prince_kab.txt --stray-u
python build_parallel.py feraoun "Le-fils-du-pauvre.pdf" ../data/feraoun_kab.txt ../data/parallel_feraoun.jsonl
python build_parallel.py petit_prince "PETIT-PRINCE.pdf" ../data/petit_prince_kab.txt ../data/parallel_petit_prince.jsonl
python extract_kabyle_pdf.py livre_5.pdf ../data/camus_kab.txt
python build_parallel.py camus "Albert_Camus_-_Kabylie.pdf" ../data/camus_kab.txt ../data/parallel_camus.jsonl
python extract_glossaries.py livre_3.pdf ../data/petit_prince_kab.txt ../data/glossaries.jsonl
```

(Supprimer `lexicon.jsonl` et `sentences.jsonl` avant de relancer le premier script : il ajoute à la fin.)

## Points connus

- Les livres HCA utilisent d'anciennes polices (« Tira », « Tayma »…) : `kabyle_fonts.py` lit la police de chaque morceau de texte et rétablit ɣ, ḍ, ṭ, ẓ, ṛ, ṣ, ḥ, ɛ, ǧ, č. Quelques mots peuvent rester mal convertis.
- Le *Lexique kabyle du corps humain* (Haddadou, HCA 2003) est un scan : il faut un OCR puis une relecture lourde. Mieux vaut obtenir la version Word d'origine auprès du HCA.
