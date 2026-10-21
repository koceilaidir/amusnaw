# Traduction et IA d'Amusnaw

## Comment une traduction est faite

Quand l'élève écrit « traduis… » (n'importe où, même en pleine leçon) :

1. **Un mot ou une courte expression** : le dictionnaire vérifié répond.
2. **Une phrase déjà traduite par un humain** (Tatoeba, livres bilingues) : on rend cette traduction, avec la mention « traduction humaine ».
3. **Sinon** : le moteur **NLLB-200** de Meta traduit, phrase par phrase. Les mots importants sont expliqués avec le dictionnaire, et on montre une phrase proche traduite par un humain.
4. **NLLB pas lancé et texte long** : le prof le dit honnêtement au lieu d'inventer.

« Corrige… » met le prof en mode correction pour la réponse.

## Lancer le moteur NLLB sur le VPS

Il faut environ 4 Go de mémoire libre pendant la construction (téléchargement et conversion du modèle), puis environ 1 Go en marche. Si le VPS est juste, arrêter Ollama le temps de la construction.

```bash
cd /opt/amusnaw/server
docker compose stop ollama            # seulement si la mémoire manque
docker compose --profile mt up -d --build mt
docker compose start ollama
docker compose logs -f mt             # attendre « Uvicorn running »
```

`MT_URL=http://mt:8100` doit être dans `.env` (valeur par défaut). Puis `docker compose up -d api`.

## Le banc d'essai

300 phrases fixes : 200 du quotidien (Tatoeba) et 100 tirées des livres (Petit Prince, Feraoun, Camus), dans les deux sens.

```bash
docker compose exec api python -m app.eval_translate
```

Le score chrF va de 0 à 100 (plus haut = mieux). Chaque nouveau modèle passe ce test, et on le garde seulement s'il fait mieux.

Premier repère, sans NLLB, en prenant la phrase humaine la plus proche :
- français → kabyle : environ 40 sur le quotidien, 21 sur les livres ;
- kabyle → français : environ 46 sur le quotidien, 22 sur les livres.

Le score « quotidien » de ce repère est flatteur : Tatoeba contient beaucoup de phrases presque identiques.

## Premiers résultats de NLLB (19 octobre 2026)

| Sens | Phrase humaine la plus proche | NLLB |
|---|---|---|
| français → kabyle, quotidien | 31,7 | **35,5** |
| français → kabyle, livres | 18,9 | **26,9** |
| kabyle → français, quotidien | 44,7 | **47,9** |
| kabyle → français, livres | 20,7 | **33,2** |

NLLB comprend bien le kabyle (vers le français), mais écrit un kabyle approximatif. Défauts vus : « grand-mère » traduit par « ma femme », noms de lieux en français (Tizi Ouzou).

## amusnaw-mt v1 en ligne (21 octobre 2026)

NLLB réentraîné sur Kaggle (1 h d'entraînement) avec 240 000 paires humaines et 300 000 paires rétro-traduites. Mesuré sur le VPS :

| Sens | NLLB de base | **amusnaw-mt** |
|---|---|---|
| français → kabyle, quotidien | 35,5 | **46,3** |
| français → kabyle, livres | 26,9 | **35,3** |
| kabyle → français, quotidien | 47,9 | **55,6** |
| kabyle → français, livres | 33,2 | **38,9** |

Pistes pour une v2 : rétro-traduire les 869 000 phrases (au lieu de 300 000), deux passages sur les données (l'entraînement n'a pris qu'une heure sur les 6 h 30 possibles).

## Étape 2 : entraîner amusnaw-mt (gratuit, sur Kaggle)

### 1. Fabriquer les données (sur le PC)

```powershell
cd C:\Users\Lenovo\OneDrive\Bureau\Minerva\IA\amusnaw\data_pipeline
python build_mt_dataset.py ..\data ..\data\mt
```

Résultat : `data\mt\amusnaw-mt-data.zip` (environ 25 Mo). Il contient :
- environ 240 000 paires humaines ;
- environ 870 000 phrases kabyles humaines ;
- le banc d'essai, dont les phrases sont retirées de tout le reste.

### 2. Lancer l'entraînement sur Kaggle

1. Créer un compte sur kaggle.com et valider le numéro de téléphone (obligatoire pour avoir le GPU et Internet).
2. **Datasets → New Dataset** : envoyer `amusnaw-mt-data.zip`, nom `amusnaw-mt-data`, visibilité **Private**.
3. **Code → New Notebook → File → Import Notebook** : `training/amusnaw_mt_kaggle.ipynb`.
4. Panneau de droite :
   - *Accelerator* : **GPU T4 x2** ;
   - *Internet* : **On** ;
   - *Add Input* : le dataset `amusnaw-mt-data`.
5. **Save Version → Save & Run All (Commit)**. Le calcul tourne seul (8 à 10 h), même ordinateur éteint.
6. À la fin, onglet **Output** : lire `rapport.json` (scores avant et après), puis télécharger `amusnaw-mt-ct2.zip` (format du serveur, environ 600 Mo). S'il n'y est pas, la conversion n'a pas marché sur Kaggle : télécharger `amusnaw-mt-hf.zip` (environ 1,2 Go) et suivre « Conversion sur le VPS » ci-dessous.

### 3. Mettre amusnaw-mt sur le VPS (seulement s'il fait mieux que NLLB)

```powershell
scp amusnaw-mt-ct2.zip root@5.39.119.109:/opt/amusnaw/
```
```bash
cd /opt/amusnaw && mkdir -p models/amusnaw-mt && cd models/amusnaw-mt && unzip -o ../../amusnaw-mt-ct2.zip
cd /opt/amusnaw/server
echo "MT_MODEL_DIR=/models_custom/amusnaw-mt" >> .env
docker compose --profile mt up -d mt
docker compose exec api python -m app.eval_translate
```
**Conversion sur le VPS** (seulement si Kaggle n'a fourni que `amusnaw-mt-hf.zip`) :
```powershell
scp amusnaw-mt-hf.zip root@5.39.119.109:/opt/amusnaw/
```
```bash
cd /opt/amusnaw && mkdir -p models && unzip -o amusnaw-mt-hf.zip -d models/amusnaw-mt-hf
cd server && docker build --target convert -t amusnaw-convert ./mt
docker compose stop ollama
docker run --rm -v /opt/amusnaw/models:/m amusnaw-convert sh -c "ct2-transformers-converter --model /m/amusnaw-mt-hf --output_dir /m/amusnaw-mt --quantization int8 --force && python -c \"from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('facebook/nllb-200-distilled-600M').save_pretrained('/m/amusnaw-mt')\""
docker compose start ollama
```
Puis les trois dernières commandes ci-dessus (`MT_MODEL_DIR`, redémarrage de `mt`, banc d'essai).

Pour revenir à NLLB de base : retirer la ligne `MT_MODEL_DIR` de `.env`, puis `docker compose --profile mt up -d mt`.

## La suite : notre propre modèle

1. **Fabrique de données** : paires humaines nettoyées, plus des paires obtenues par rétro-traduction (vrai kabyle humain traduit vers le français par NLLB). On n'entraîne jamais sur du kabyle écrit par une machine.
2. **amusnaw-mt** : NLLB réentraîné sur ces données (GPU gratuit de Kaggle), remplace le modèle du service `mt` s'il fait mieux au banc d'essai.
3. **amusnaw-v1** : petit modèle de conversation (Qwen) entraîné à expliquer, corriger et faire des leçons, servi par Ollama.

**Licences :**
- NLLB est sous CC BY-NC 4.0 : Amusnaw reste gratuit, donc c'est compatible.
- Tatoeba : CC BY 2.0 FR, la source doit être citée.
- Le livre de Bouamara (CC BY-NC-ND) est exclu de l'entraînement.
