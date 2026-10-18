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

## La suite : notre propre modèle

1. **Fabrique de données** : paires humaines nettoyées, plus des paires obtenues par rétro-traduction (vrai kabyle humain traduit vers le français par NLLB). On n'entraîne jamais sur du kabyle écrit par une machine.
2. **amusnaw-mt** : NLLB réentraîné sur ces données (GPU gratuit de Kaggle), remplace le modèle du service `mt` s'il fait mieux au banc d'essai.
3. **amusnaw-v1** : petit modèle de conversation (Qwen) entraîné à expliquer, corriger et faire des leçons, servi par Ollama.

**Licences :**
- NLLB est sous CC BY-NC 4.0 : Amusnaw reste gratuit, donc c'est compatible.
- Tatoeba : CC BY 2.0 FR, la source doit être citée.
- Le livre de Bouamara (CC BY-NC-ND) est exclu de l'entraînement.
