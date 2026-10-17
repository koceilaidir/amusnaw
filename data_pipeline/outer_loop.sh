#!/bin/bash
# Boucle : apprendre → réaligner les livres traduits → réapprendre, avec mesures à chaque tour.
set -e
U=/root/.claude/uploads/4d0a5699-ac07-5264-8a09-fea839f824ef
for tour in 1 2 3; do
  echo "################ GRAND TOUR $tour"
  python3 learn_lexicon.py ../data | grep -v '^   '
  python3 build_parallel.py feraoun $U/7d0d8a89-Le-fils-du-pauvre-Mouloud-Feraoun-Feraoun-Mouloud.pdf ../data/feraoun_kab.txt ../data/parallel_feraoun.jsonl
  python3 build_parallel.py petit_prince $U/1917551a-PETIT-PRINCE-LE-Antoine-de-Saint-Exupery.pdf ../data/petit_prince_kab.txt ../data/parallel_petit_prince.jsonl
  python3 build_parallel.py camus $U/c9666bbc-Albert_Camus_-_Kabylie.pdf ../data/camus_kab.txt ../data/parallel_camus.jsonl
  python3 audit_parallel.py ../data/parallel_*.jsonl
  python3 lemmatize.py
done
