#!/bin/bash
# Reconstruit TOUTE la base kabyle d'Amusnaw à partir des livres HCA, dans l'ordre.
# Chaque étape profite des précédentes (corrections de caractères → lemmatiseur →
# alignement → apprentissage → réalignement…).
#
#   ./rebuild_all.sh <dossier des livres HCA> <dossier des PDF isolés>
#     - dossier des livres : <année>/<nn-titre>/livre.pdf + infos.txt
#     - PDF isolés : traductions françaises (Petit Prince, Fils du pauvre, Camus),
#       Bouamara (Apprendre le kabyle par niveaux, Lexique de la rhétorique)
#
# Le lexique du corps humain (data/lexicon_corps_humain.jsonl) est une transcription
# manuelle d'un scan : il n'est pas régénéré.
set -euo pipefail
cd "$(dirname "$0")"
PDF="${1:-/mnt/user-data/uploads/pdf}"
UP="${2:-/root/.claude/uploads/4d0a5699-ac07-5264-8a09-fea839f824ef}"
D=../data
TXT=$(mktemp -d)
echo "== 1. Corpus kabyle des livres HCA (anciennes polices converties, autres variantes exclues)"
python3 build_corpus.py "$PDF" $D/corpus_hca.jsonl $D/word_freq.tsv | tail -1
python3 build_poetry.py "$PDF" $D/corpus_poesie.jsonl | tail -1

echo "== 2. Lexiques HCA"
python3 parse_amawal_tatrart.py "$PDF"/2004/04-*/livre.pdf $D/lexicon_tatrart.jsonl | tail -1
python3 parse_amawal_akal.py "$PDF"/2004/03-*/livre.pdf $D/lexicon_terre_animaux.jsonl | tail -1
python3 pdf_lines.py "$PDF"/2013/02-*/livre.pdf $TXT/didactique.txt
python3 parse_didactique.py $TXT/didactique.txt $D/lexicon_didactique.jsonl | tail -1
python3 parse_prenoms.py "$PDF"/2003/03-*/livre.pdf $D/lexicon_prenoms.jsonl | tail -1
python3 pdf_lines.py "$PDF"/2013/01-*/livre.pdf $TXT/jur2013.txt
python3 pdf_lines.py "$PDF"/2021/03-*/livre.pdf $TXT/jur2021.txt
python3 parse_juridique.py $TXT/jur2013.txt $TXT/jur2021.txt $D/lexicon_juridique.jsonl | tail -1
python3 extract_book_glossaries.py "$PDF" $D/lexicon_glossaires_livres.jsonl | tail -1
python3 parse_tinfaliyin.py "$PDF"/2025/12-*/livre.pdf $D/tinfaliyin.jsonl
python3 parse_rhetorique.py "$UP"/*Lexique_rhetorique*.pdf $D/lexicon_rhetorique.jsonl $D/corpus_rhetorique.jsonl
python3 parse_bouamara_niveaux.py "$UP"/*document_2.pdf $D/bouamara_niveaux.jsonl

echo "== 2b. Lexique des animaux marins, textes kabyles des livres traduits et leurs glossaires"
rm -f $D/lexicon.jsonl $D/sentences.jsonl
python3 extract_amawal_iselman.py "$UP"/*livre_2.pdf $D | tail -1
python3 extract_kabyle_pdf.py "$UP"/*livre_3.pdf $D/feraoun_kab.txt
python3 extract_kabyle_pdf.py "$UP"/*livre_4.pdf $D/petit_prince_kab.txt --stray-u
python3 extract_kabyle_pdf.py "$UP"/*livre_5.pdf $D/camus_kab.txt
python3 extract_glossaries.py "$UP"/*livre_3.pdf $D/petit_prince_kab.txt $D/glossaries.jsonl | tail -1

echo "== 3. Corrections de caractères (anciennes polices)"
python3 fix_chars.py $D

echo "== 3b. Ressources libres (data/externes) : Hunspell, maths, Tatoeba (anglais, français), logiciels, contes, toponymes, Wikipédia"
python3 import_lexicons_ext.py $D
python3 import_tatoeba.py $D          # phrases d'abord (preuves d'usage des verbes)
python3 import_memoire_traduction.py $D
python3 import_ressources_libres.py $D   # Tatoeba fr, contes, toponymes, Wikipédia, kabyle-corpus

echo "== 4. Verbes : courants (attestés), puis trouvés dans les lexiques"
python3 validate_core_verbs.py $D ../server/content/verbs.json
python3 expand_verbs.py $D ../server/content/verbs.json
python3 import_verbs.py $D ../server/content/verbs.json   # 6 198 tables (taqbaylit/kabyle-verbs)
python3 discover_verbs.py $D ../server/content/verbs.json | sed -n 2p

echo "== 5. Textes traduits : alignement par lemmes ↔ apprentissage, en boucle"
for tour in 1 2; do  # converge en 2 tours (mesuré)
  echo "-- grand tour $tour"
  python3 learn_lexicon.py $D | grep -v '^   '
  python3 build_parallel.py feraoun "$UP"/*Le-fils-du-pauvre*.pdf $D/feraoun_kab.txt $D/parallel_feraoun.jsonl
  python3 build_parallel.py petit_prince "$UP"/*PETIT-PRINCE*.pdf $D/petit_prince_kab.txt $D/parallel_petit_prince.jsonl
  python3 build_parallel.py camus "$UP"/*Albert_Camus*.pdf $D/camus_kab.txt $D/parallel_camus.jsonl
  python3 audit_parallel.py $D/parallel_*.jsonl
done
python3 learn_lexicon.py $D | grep -v '^   '
python3 learn_lexicon.py $D --holdout | sed -n 1,6p
python3 learn_english.py $D | tail -1
python3 learn_english.py $D --eval | grep "référence"
python3 import_tatoeba.py $D          # exemples citables avec le lemmatiseur complet

echo "== 6. Bilan"
python3 lemmatize.py
cp function_words.json ../server/content/function_words.json
rm -rf "$TXT"
