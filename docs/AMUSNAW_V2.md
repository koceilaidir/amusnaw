# amusnaw-v2 et amusnaw-mt v2

## Ce qui change par rapport à la v1

**Nouvelles données (autorisations obtenues par le HCA, octobre 2026)** :
- Assimil, *Kabyle de poche* : 875 phrases et mots du quotidien, 10 petits dialogues (saluer, se présenter, au café, à l'épicerie, au téléphone…) ;
- K. Bouamara, *Apprendre le kabyle par niveaux* : 1 009 entrées vérifiées par l'auteur ;
- J.-M. Dallet, *Dictionnaire français-kabyle* : 1 249 mots sûrs (le reste attend une relecture).

**amusnaw-v2 (le prof)** :
- de vraies discussions : l'élève écrit en kabyle, le prof répond en kabyle simple, traduit et relance ; dialogues tour par tour ;
- 1 500 réponses « je ne sais pas » (la même phrase que le serveur) ;
- le vrai prompt du serveur dans 15 % des exemples (6 % en v1) ;
- moins de traduction et de correction automatiques, moins de lecture brute : l'entraînement doit aller jusqu'au bout ;
- le temps d'entraînement s'adapte au temps restant de la séance Kaggle.

**amusnaw-mt v2 (le traducteur)** : 600 000 phrases rétro-traduites (300 000 en v1), 2 passages, Assimil ×4 et Bouamara ×3.

## Lancer sur Kaggle

1. Fabriquer les données sur le PC :
   ```powershell
   cd C:\Users\Lenovo\OneDrive\Bureau\Minerva\IA\amusnaw\data_pipeline
   python build_mt_dataset.py ..\data ..\data\mt
   $env:DATA_DIR="..\data"; $env:CONTENT_DIR="..\server\content"; $env:PROMPTS_DIR="..\server\prompts"
   python build_chat_dataset.py
   ```
   (ou utiliser directement les zips fournis par Claude.)
2. Kaggle → **Datasets** : mettre à jour `amusnaw-mt-data` (New Version) avec le nouveau `amusnaw-mt-data.zip`, et créer `amusnaw-v2-data` (Private) avec `amusnaw-v2-data.zip`.
3. Importer `training/amusnaw_mt_kaggle.ipynb` et `training/amusnaw_v2_kaggle.ipynb` (deux carnets, deux séances : on peut les lancer le même jour).
4. Pour chaque carnet : GPU T4 x2, Internet On, Add Input le bon jeu de données, puis **Save & Run All (Commit)**.
5. Installer seulement si le rapport (`rapport.json`, `rapport_v2.json`) est meilleur. Même procédure qu'en v1 (docs/TRADUCTION.md, docs/AMUSNAW_V1.md), en remplaçant v1 par v2.

## Résultats (24 octobre 2026)

- **amusnaw-mt v2 : installé** (voir docs/TRADUCTION.md), meilleur que la v1 sur les quatre tests.
- **amusnaw-v2 : non installé.** Entraînement complet (502/502 pas), mais traduction 27,1 / 38,3 (v1 : 32,5 / 44,4) et correction parfaite 53 % (v1 : 60 %). Il ne répond plus « On continue ? » et dit « je ne sais pas », mais il répond en français aux salutations kabyles et a inventé « Yennayer le 12 février ». Leçon : un modèle de 3 milliards de paramètres perd en traduction et en correction quand on ajoute de la discussion générée. La discussion reste confiée à Qwen encadré par le serveur ; une v3 attendra de vraies conversations relues (/review).
