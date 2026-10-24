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
| `lexicon_tatrart.jsonl` | H. A. Mansouri, *Amawal n tmaziɣt tatrart* (HCA 2004) — 3 536 mots modernes, français → kabyle | dictionnaire du prof |
| `lexicon_terre_animaux.jsonl` | A. Z. Yeddir, lexique des sciences de la terre + lexique animal (HCA 2004) — 236 entrées | dictionnaire, culture du village |
| `lexicon_didactique.jsonl` | M. Mahrazi, *Lexique de didactique et des sciences du langage* (HCA 2013) — 1 818 termes | vocabulaire de la classe, grammaire |
| `lexicon_prenoms.jsonl` | M. A. Haddadou, *Recueil de prénoms amazighs* (HCA 2003) — 1 117 prénoms et leur sens | sujet « prénoms amazighs » |
| `lexicon_juridique.jsonl` | M. Z. Benramdane, *Amawal azerfan* (2013) et *Amawal n tutlayt tazerfant* (2021) — 7 784 termes | dictionnaire (poids réduit dans la recherche) |
| `phrases_juridiques.jsonl` | Les 26 545 longues expressions des mêmes lexiques | non chargé par le prof ; réservé à l'entraînement |
| `lexicon_corps_humain.jsonl` | M. A. Haddadou, *Lexique kabyle du corps humain* (HCA 2003), transcrit depuis le scan — 87 entrées (66 noms, 21 verbes), 595 expressions (421 traduites), 22 devinettes. Champ `unsure` : lectures douteuses (ɣ/y surtout) | dictionnaire, phrases citables, unité « Le corps » |
| `bouamara_niveaux.jsonl` | K. Bouamara, *Lmed taqbaylit s yiswiren – Apprendre le kabyle par niveaux* (HAL hal-05580987, 2026, **CC BY-NC-ND 4.0**) — 1 009 entrées kabyle / français / anglais, niveaux 0 (mots) à 5 (expert), traduction littérale (`lit`) quand elle existe. Vérifié par l'auteur | citations du prof (avec la source), vocabulaire de base. **Autorisation de l'auteur obtenue par le HCA (octobre 2026) pour améliorer l'IA d'Amusnaw : utilisé pour l'entraînement (amusnaw-mt, amusnaw-v2) et la mémoire de traduction.** Garder l'autorisation écrite. |
| `lexicon_rhetorique.jsonl` | K. Bouamara, *Amawal n tunuɣin n tesnukyest – Lexique de la rhétorique* (HCA 2007) — 83 termes | dictionnaire (langue et didactique) |
| `corpus_rhetorique.jsonl` | Le même livre : 279 phrases kabyles de l'essai | exemples d'emploi |
| `tinfaliyin.jsonl` | A. At Weḥmana, *Tinfaliyin n Tmaziɣt-Taqbaylit* (HCA 2025) — 5 818 expressions kabyles avec traduction française. **Orthographe de l'auteur** (préfixes séparés : « I nna-yas ») : citées comme telles | expressions, sens des mots |
| `lexicon_tinfaliyin.jsonl` | Le même livre : 1 541 mots d'entrée et leurs sens | dictionnaire |
| `lexicon_glossaires_livres.jsonl` | Glossaires de fin de livre : *Abane Ramdane*, *Llawel*, *Inagan*, *Imseɣret aɣelnaw*, *Akeččum ɣer tefyirmant*, *Tizizwit d tamemt* (apiculture) — 492 mots | dictionnaire |
| `corpus_poesie.jsonl` | 3 742 strophes de 7 recueils (*Inagan*, *Llawel*, *Iḥulfan d izuffan*, *Amsebrid*, *Teyzi n yiles*, *Tiɣri n Umesdrar*, *Ayen i d-nnan ger yetran*), découpées par strophe | poésie, exemples d'emploi |
| `corpus_hca.jsonl` | 45 673 phrases kabyles authentiques tirées de 43 livres HCA (romans, contes, poésie, essais, histoire) | exemples d'emploi réel, fréquence des mots, pré-entraînement |
| `word_freq.tsv` | Fréquence de chaque forme kabyle dans ce corpus | choix du vocabulaire courant, vérification des mots du programme |

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

Le programme A1 (`server/content/curriculum_a1.json`) n'utilise que des mots attestés dans ce corpus ou ces lexiques (vérifié avec `word_freq.tsv`).

Livres **non intégrés** : variétés autres que le kabyle (touareg, mozabite, chaoui, Ouargla, Atlas blidéen), actes de colloques en français ou en arabe, et les ouvrages qui ne sont pas des publications HCA (Assimil, Naït-Zerrad, Mammeri chez Maspero, paroles de chansons) : l'autorisation du HCA ne les couvre pas.

```bash
python build_corpus.py <dossier des livres> ../data/corpus_hca.jsonl ../data/word_freq.tsv
python parse_amawal_tatrart.py ; python parse_amawal_akal.py ; python parse_didactique.py
python parse_prenoms.py ; python parse_juridique.py
```

## Ressources libres ajoutées (oct. 2026) — `data/externes/` → `import_*.py`

| Source (Hugging Face) | Licence | Fichiers d'origine → `data/externes/` | Ce qu'on en tire |
|---|---|---|---|
| `taqbaylit/kabyle-verbs` (tables issues du conjugueur **amyag.com**) | CC BY 4.0 déclarée | `train-0000{0,1,2}-of-00003.parquet` → `verbes_tables_{0,1,2}.parquet` ; formes : `train-0000{0..5}-of-00006.parquet` → `verbes_formes_{0..5}.parquet` | **6 198 verbes** avec sens français et conjugaison complète (`import_verbs.py`) ; croisés forme par forme avec nos règles (aoriste 98-100 % d'accord) ; Bouamara reste la référence pour ses verbes. **Provenance amyag.com à signaler au HCA.** |
| `taqbaylit/tatoeba-en-kab` (Tatoeba) | CC0 / CC BY 2.0 FR | `train-00000-of-00001.parquet`, `dev-00000-of-00001.parquet` → `tatoeba_en_kab_{train,dev}.parquet` | 204 941 phrases kabyles (preuves d'usage des verbes, `tatoeba_kab.jsonl`), 60 000 exemples citables (`tatoeba_exemples.jsonl`), **3 693 sens anglais appris** (`learn_english.py`, ≈ 95 % justes à la relecture) |
| `taqbaylit/kabyle-english-TM` (logiciels libres) | CC BY 4.0 | `kab_en_translation_memory.parquet` → `memoire_traduction_en_kab.parquet` | **29 977 termes modernes** kabyle ↔ anglais (`termes_modernes_en.jsonl`) |
| `agbalu/KabLex` | CC BY 4.0 / MIT | `train (1).jsonl` → `kablex_lexicon.jsonl`, `train.jsonl` → `kablex_prononciations.jsonl` | lexique de mathématiques Tafsut : **3 668 termes** (`lexicon_maths.jsonl`) |
| `boffire/hunspell-kab` (correcteur, M. Belkacem) | MIT | `kab.dic`, `kab.aff` | **21 810 mots** avec nature et mot de base (pluriels, féminins) → lemmatiseur (`hunspell_kab.jsonl`) |

**Bilan** : 6 269 verbes conjugués ; **89,3 % des mots du corpus HCA reconnus** (77,5 % avant ces ressources) ; phrases décalées des livres traduits 6,4 % (Camus), 10,5 % (Feraoun), 1,8 % (Petit Prince) ; test caché 82 % (strict).

## Quatrième passe : ressources kabyle ↔ français (17 oct. 2026) — `import_ressources_libres.py`

| Source | Licence | Fichier d'origine → `data/externes/` | Ce qu'on en tire |
|---|---|---|---|
| Tatoeba kabyle-français | CC BY 2.0 FR | `fr_kab_tifinagh.tsv` → `tatoeba_fr_kab_tifinagh.tsv` ; `Sentence pairs in Kabyle-French - 2023-07-18.tsv` → `tatoeba_kab_fr_2023.tsv` ; `en_kab_tifinagh.tsv` → `tatoeba_en_kab_tifinagh.tsv` | **225 983 paires kabyle-français** (`tatoeba_fr.jsonl`) : apprentissage des sens **français** et exemples traduits en français |
| Tatoeba, toutes les phrases kabyles | CC BY 2.0 FR | `kab_tifinagh.tsv` → `tatoeba_kab_tifinagh.tsv` | 758 143 phrases (`tatoeba_kab_tout.jsonl`) : preuves d'usage |
| Contes *timucuha* (association Numidya) | CC BY-NC 4.0 (anglais traduit par machine) | `train (2).jsonl`, `validation.jsonl` → `contes_numidya_{train,val}.jsonl` | 917 phrases kabyle-français (`contes_numidya.jsonl`) |
| Toponymes OpenStreetMap | ODbL (© contributeurs OSM) | `train-00000-of-00001 (2).parquet` → `toponymes_osm.parquet` | 5 344 noms de lieux kabyles (villes, villages, daïras, reliefs ; rues et commerces écartés) → `toponymes.jsonl` |
| Wikipédia en kabyle | CC BY-SA 4.0 | `WIKABV1.zip` → `wikab_v1.zip` ; `kabwiki_*.txt.gz` → `kabwiki/` | 5 594 articles, 12 357 passages gardés s'ils sont bien en kabyle (≥ 70 % de mots reconnus) → `wiki_kab.jsonl` |
| Common Voice (Mozilla), phrases kabyles | CC0 | dépôt GitHub `common-voice/server/data/kab/*.txt` → `commonvoice_kab/` | 168 341 phrases (`commonvoice_kab.jsonl`) : preuves d'usage |
| kabyle-corpus (`data.csv`) | MIT, origine inconnue, bruité | `data.csv` → `corpus_kabyle_data.csv` | seulement les 311 240 phrases dont tous les mots sont reconnus (`attestation_kab.jsonl`) : fréquences et preuves d'usage, **jamais citées** |
| Entités nommées kabyle-anglais | non précisée | `kabyle_named_entities.tsv` | 292 entités (`entites_nommees_en.jsonl`), en réserve |

**Écartés** : traductions du Coran et de la Bible (sensibles, droits des traductions), paires « minées » NLLB (trop bruitées), téléchargements incomplets (`.crdownload`).

**Bilan** : 6 346 verbes ; **90,3 % des mots du corpus HCA reconnus** (89,3 % avant) ; 270 600 formes connues, 18 022 lemmes avec un sens français ; **3 221 traductions apprises** (≈ 320 avant), test caché 74 % strict, ≈ 90 % à la relecture ; les sens appris ne sont jamais préférés à un sens HCA : ils apparaissent en « autres sens » ou en dernier recours.

## Troisième passe : lemmatiseur et apprentissage (oct. 2026)

Tout se reconstruit avec `data_pipeline/rebuild_all.sh <livres> <pdf isolés>`.

- **Lemmatiseur** (`lemmatize.py`, copie serveur `server/api/app/morph.py`) : ramène chaque forme à son lemme sans rien inventer — mots-outils (`function_words.json`), verbes conjugués par les règles de Bouamara (+ variante « ye- », participes), noms à l'état libre / annexé / pluriels listés, pronoms collés, noms propres (majuscule > 80 %).
- **Verbes courants** (`core_verbs.json` → `validate_core_verbs.py`) : ili, ẓer, bɣu, zmer, sɛu, ṭṭef… gardés seulement si le corpus atteste leurs formes ; un aspect sans preuve est retiré.
- **Autres variantes exclues du corpus kabyle** : *Tirmeǧǧut* et *Aḍu n Unẓul* (chaoui), *Inhiten d tinẓuren n imuhaɣ* et *tinfosen nanr* (touareg), livret en arabe.
- **Alignement des livres traduits par lemmes** (`lexsim.py`, `build_parallel.py`) et contrôle anti-décalage (`audit_parallel.py`).
- **Verbes découverts** (`discover_verbs.py`) : formes inconnues vues après « ad » → lemme possible → conjugaison complète par les règles → gardé si le corpus atteste ses formes (aoriste ≥ 3, prétérit ≥ 2, total ≥ 8). Variantes et doublons écartés (même squelette consonantique et même place des voyelles). Sens rattachés ensuite : apprentissage, nom verbal de Tinfaliyin (modèle régulier), ou même mot dans un lexique HCA ; sinon « sens non encore relevé ».
- **Apprentissage** (`learn_lexicon.py` → `lexicon_appris.jsonl`, domaine `appris`, poids faible, à valider) : liaison compétitive lemme kabyle ↔ racine française sur les paires fiables ; au moins 3 paires et Dice ≥ 0,3 (≥ 0,6 pour les mots de 3 lettres). Précision mesurée par test caché (20 % des mots connus masqués puis retrouvés) : 74 % en comparaison automatique stricte, ≈ 93 % à la relecture (la plupart des « erreurs » sont des erreurs de la référence ou des synonymes).

**Bilan de la reconstruction complète** : 41 387 phrases kabyles + 3 742 strophes ; 271 verbes conjugués (35 Bouamara, 8 ajoutés, 42 courants attestés, 53 des lexiques, 133 découverts dont 34 avec un sens) ; 359 traductions apprises ; livres traduits : phrases décalées 7,6 % (Camus), 11,5 % (Feraoun), 2,1 % (Petit Prince), 2 611 paires fiables ; **77,5 % des mots du corpus reconnus** (lemme + analyse), contre 65,6 % au début de cette passe. Le corpus de Bouamara est utilisé pour apprendre depuis l'autorisation obtenue par le HCA (octobre 2026).

## Points connus

- **Seconde passe (oct. 2026)** : `fix_chars.py` corrige les restes d'anciennes polices ($ → ɣ, £ → Ɣ, ɤ → ɣ, є → ɛ, Σ → Ɛ, << >> → « », caractères invisibles) : ~2 600 phrases réparées ; les 67 phrases contenant « „ » (u ou y selon le livre, ambigu) sont retirées. Les corpus parallèles ont été réalignés avec le dictionnaire (`lexsim.py`) : phrases décalées (la voisine correspond mieux) passées de 24 % à 15 % pour Feraoun, 13 % à 11 % pour Camus ; les paires restantes douteuses sont marquées `confident: false` et ne sont jamais citées.

- Les livres HCA utilisent d'anciennes polices (« Tira », « Tayma »…) : `kabyle_fonts.py` lit la police de chaque morceau de texte et rétablit ɣ, ḍ, ṭ, ẓ, ṛ, ṣ, ḥ, ɛ, ǧ, č. Quelques mots peuvent rester mal convertis.
- Le *Lexique kabyle du corps humain* a été transcrit à la main depuis le scan : dans la police italique, ɣ et y se ressemblent. Les mots douteux sont listés dans le champ `unsure` de chaque entrée : à relire en priorité.
- Conjugaison : `server/content/verbs.json` (92 verbes : 35 tirés des tableaux de Bouamara, 8 ajoutés à la main, 49 trouvés dans les lexiques HCA par `data_pipeline/expand_verbs.py` et gardés seulement si le corpus atteste leurs formes — preuves dans le champ `attested`) + règles de K. Bouamara (HAL hal-05647626, 2026, CC BY-NC-SA 4.0) dans `server/api/app/conjugation.py`, testées sur les 180 formes de ses tableaux. Les verbes marqués `source: amusnaw` sont à faire valider.
- Le corpus par niveaux est un tableau à 3 colonnes : `parse_bouamara_niveaux.py` regroupe les lignes par rangée (pas « en miroir » ligne à ligne), recolle les entrées coupées par un saut de page et retrouve exactement les 1 009 entrées annoncées. Contrôle : sur 99 mots communs avec les lexiques HCA, les écarts restants sont des synonymes.
- Fiches de grammaire : `server/content/grammar_notes.json` (12 fiches rédigées pour Amusnaw, exemples tirés de la base) ; *Ilugan n tira n tmaziɣt* (éd. Iman-nneɣ, droits réservés) a servi de référence, sans en reprendre le texte.
- Non intégrés (droits non couverts par l'autorisation du HCA) : Dallet, *Dictionnaire kabyle-français* (SELAF 1982), mémoires de master de l'UMMTO et de l'UQAM, article de Ben Mohamed (*Expressions maghrébines*, 2016).

## Sources ajoutées en octobre 2026 (autorisations obtenues par le HCA)

Autorisation des auteurs / éditeurs obtenue par le HCA (octobre 2026), **pour améliorer l'IA d'Amusnaw** : Dallet, Assimil, Naït-Zerrad, Mammeri (Maspero), mémoires de l'UMMTO et de l'UQAM, article de Ben Mohamed, paroles de chansons. Garder les autorisations écrites.

| Fichier | Source | Comment | Usage |
|---|---|---|---|
| `assimil_poche.jsonl` | F. Amazit-Hamidchi, *Kabyle de poche*, Assimil, 2007 | PDF scanné : pages de conversation lues et transcrites à la main (orthographe kabyle moderne), 875 entrées dont 10 petits dialogues (`dialogue`) | paires de traduction (×4), discussions d'amusnaw-v2, mémoire de traduction |
| `dallet_fk.jsonl` | J.-M. Dallet, *Dictionnaire français-kabyle*, SELAF, 1985 | couche de texte OCR ancienne ; formes kabyles restaurées à partir du kabyle attesté (`parse_dallet_fk.py`, `kab_vocab.py`) ; `confident=true` pour ~19 % des entrées | entrées sûres → paires de mots ; le reste attend une relecture |
| `externes/ocr/naitzerrad_*.txt` | K. Naït-Zerrad, *Manuel de conjugaison kabyle* | OCR (tesseract) ; ɣ/ɛ souvent abîmés | pas encore utilisé : servira à vérifier et étendre nos conjugaisons |
| `externes/ocr/mammeri_*.txt`, `mammeri_tajerrumt.jsonl` | M. Mammeri, *Tajerrumt n tmaziɣt*, Maspero, 1976 | OCR de qualité insuffisante (185 phrases sûres seulement) | pas utilisé pour l'entraînement |
