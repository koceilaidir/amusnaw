# amusnaw-v1 : le prof de kabyle qui discute

**amusnaw-v1** est Qwen2.5-3B-Instruct (le modèle actuel du VPS) réentraîné avec un adaptateur LoRA sur nos données kabyles. Il garde la même taille et la même vitesse que l'actuel.

## Ce qu'il apprend

Toutes les réponses d'entraînement sont écrites par la machine **à partir de données vérifiées** : rien n'est inventé.

| Type | Nombre | D'où viennent les réponses |
|---|---|---|
| Traduction fr → kab | ~27 000 | paires humaines (Tatoeba, livres, contes, expressions) |
| Traduction kab → fr | ~22 000 | idem |
| Correction | 25 000 | vraie phrase humaine dans laquelle on glisse 1 ou 2 fautes typiques (ɣ → g, ɛ → e, lettres emphatiques, trait d'union oublié, « ur … ara » incomplet) ; le prof rend la bonne phrase et explique chaque faute. 15 % des phrases sont déjà justes : il doit savoir le dire. |
| Vocabulaire | ~7 000 | dictionnaires, avec une vraie phrase d'exemple de Tatoeba quand il y en a une |
| Conjugaison | ~360 | nos règles de conjugaison, sur les verbes du programme, du corpus et de Bouamara (CC BY-NC-SA). Les tables amyag sont exclues tant que leur auteur n'a pas donné son accord. |
| Leçons guidées | 400 dialogues | le programme A1 du serveur (pas, réponses justes ou presque justes) |
| Grammaire, culture, hors-sujet | ~450 | notes de grammaire, capsules culturelles, refus poli |
| Lecture du kabyle | 150 000 phrases | kabyle humain (Tatoeba, livres, Wikipédia, Common Voice) |

Environ 6 % des exemples utilisent le **vrai prompt du serveur** avec les « RÉFÉRENCES VALIDÉES » : le modèle apprend à s'en servir.

## Résultats de la première version (21 octobre 2026)

Entraînement de 6 h sur Kaggle, arrêté à 600 pas sur 814 : il n'a vu qu'environ 74 % des données. La perte de contrôle est passée de 3,72 à 0,63.

| Test (phrases jamais vues) | Qwen 3B de base | **amusnaw-v1** |
|---|---|---|
| Traduction français → kabyle (chrF) | 7,2 | **32,5** |
| Traduction kabyle → français (chrF) | 4,7 | **44,4** |
| Correction parfaite | 0 % | **60 %** |
| Correction (chrF) | 26,7 | **93,2** |

Ce qu'on a vu sur les questions types :
- **Bien** : explication de mot avec exemple, conjugaison, format des leçons, refus du hors-sujet.
- **Faux** :
  - la traduction de « Ma grand-mère prépare le couscous le vendredi » : amusnaw-mt fait mieux, et c'est lui qui traduit sur le site ;
  - « isem-inu Koceila » : faute de possessif, un type de faute qu'il n'a pas appris ;
  - Yennayer : faits inventés. Les questions de culture sont donc désormais servies par les fiches vérifiées (`router.capsule_reply`).

**En ligne, le défaut principal est apparu tout de suite :**
- à « Azul ! Amek telliḍ ? » ou « oui », il répond « On continue ? » ;
- **cause 1** : les données ne contenaient aucune vraie discussion libre ;
- **cause 2** : 81 réponses passe-partout « On continue ? » venaient des leçons simulées ;
- **cause 3** : le long prompt du serveur n'était présent que dans 6 % des exemples, et surtout dans les leçons.

Décision : Qwen de base reste le modèle de discussion (`LLM_MODEL=qwen2.5:3b`), et amusnaw-v1 ne répond qu'aux demandes de correction (`LLM_MODEL_CORRECT=amusnaw-v1`), où il fait 60 % de corrections parfaites contre 0 %.

Pistes pour la v2 :
- **de vraies discussions**, en kabyle simple, à partir des dialogues du programme et de dialogues relus par un linguiste ;
- **des exemples où Qwen garde ses réponses d'origine** sur des questions générales, pour qu'il n'oublie pas comment discuter ;
- **le prompt du serveur** dans une grande partie des exemples ;
- plus aucune réponse passe-partout ;
- entraîner jusqu'au bout, en reprenant là où la v1 s'est arrêtée ;
- ajouter des réponses « je ne sais pas » pour les faits absents de la base ;
- ajouter les fautes de possessif (inu → iw) et de genre ;
- ajouter les dialogues relus par un linguiste.

## Fabriquer les données (sur le PC)

D'abord `build_mt_dataset.py` (déjà fait pour amusnaw-mt), puis :
```powershell
cd C:\Users\Lenovo\OneDrive\Bureau\Minerva\IA\amusnaw\data_pipeline
python build_chat_dataset.py
```
Résultat : `data\chat\amusnaw-v1-data.zip` (environ 13 Mo).

## Entraîner sur Kaggle

1. **Datasets → New Dataset** : envoyer `amusnaw-v1-data.zip`, nom `amusnaw-v1-data`, visibilité **Private**.
2. **Code → New Notebook → File → Import Notebook** : `training/amusnaw_v1_kaggle.ipynb`.
3. Panneau de droite :
   - *Accelerator* : **GPU T4 x2** ;
   - *Internet* : **On** ;
   - *Add Input* : `amusnaw-v1-data` (vérifier qu'il apparaît sous *Input*).
4. **Save Version → Save & Run All (Commit)**. Environ 7 à 8 h au total : banc d'essai avant, au plus 6 h d'entraînement, banc d'essai après, export.
5. Dans **Logs**, toutes les 200 étapes : `pas …  perte …  contrôle …`. Le chiffre « contrôle » doit baisser.
6. **Output**, à la fin :
   - `rapport_v1.json` : scores avant et après (traduction, correction) ;
   - `amusnaw-v1-q4_k_m.gguf` (environ 2 Go), ou `amusnaw-v1-q8_0.gguf` (environ 3,3 Go) si la compression n'a pas marché ;
   - `Modelfile`.

Le journal montre aussi les réponses du modèle à quelques questions types : traduction, correction, « Je veux apprendre », conjugaison, Yennayer, hors-sujet.

## Installer sur le VPS (seulement si le rapport est meilleur)

Le fichier fait 2 Go. Plutôt que de passer par le PC (connexion lente), le VPS le télécharge directement depuis Kaggle.

1. Kaggle → ton avatar → **Settings → API → Create New Token**. Le fichier `kaggle.json` est téléchargé sur le PC.
2. Sur le PC :
   ```powershell
   ssh root@5.39.119.109 "mkdir -p /root/.kaggle"
   scp $HOME\Downloads\kaggle.json root@5.39.119.109:/root/.kaggle/kaggle.json
   ```
3. Sur le VPS. Remplacer `UTILISATEUR/NOM-DU-CARNET` par la fin de l'adresse du carnet, `kaggle.com/code/UTILISATEUR/NOM-DU-CARNET` :
   ```bash
   chmod 600 /root/.kaggle/kaggle.json
   mkdir -p /opt/amusnaw/models/v1
   docker run --rm -v /root/.kaggle:/root/.kaggle:ro -v /opt/amusnaw/models/v1:/out python:3.12-slim \
     sh -c "pip install -q kaggle && kaggle kernels output UTILISATEUR/NOM-DU-CARNET -p /out"
   ls -lh /opt/amusnaw/models/v1
   ```
4. Créer le modèle dans Ollama et le brancher :
   ```bash
   cd /opt/amusnaw/server
   G=$(ls ../models/v1/*.gguf | head -1)
   docker compose cp "$G" ollama:/root/$(basename "$G")
   docker compose cp ../models/v1/Modelfile ollama:/root/Modelfile
   docker compose exec ollama sh -c "cd /root && ollama create amusnaw-v1 -f Modelfile && ollama stop qwen2.5:3b; ollama list"
   sed -i 's/^LLM_MODEL=.*/LLM_MODEL=amusnaw-v1/' .env
   docker compose up -d api
   docker compose logs -f api     # attendre « modèle chargé et gardé en mémoire » (plusieurs minutes : disque lent)
   ```
5. Pour revenir à l'ancien modèle : `sed -i 's/^LLM_MODEL=.*/LLM_MODEL=qwen2.5:3b/' .env && docker compose up -d api`.

## Licences

- Qwen2.5-3B est sous « Qwen Research License » (usage non commercial) : compatible tant qu'Amusnaw est gratuit.
- Le livre de Bouamara (niveaux, CC BY-NC-ND) est exclu.
- Les sources HCA sont utilisées avec l'autorisation du HCA (voir `data/README.md`).

## Limites

amusnaw-v1 reste un petit modèle. Il devrait mieux écrire le kabyle et mieux suivre la pédagogie, mais il garde un raisonnement limité.

Les traductions longues passent toujours par amusnaw-mt, et les leçons par le serveur. amusnaw-v1 sert à la discussion, aux explications et aux corrections.
