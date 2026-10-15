# Chansons kabyles

Module « Understand songs » : le prof explique un vers mot par mot, puis son sens littéral et son **sens caché** (images, exil, identité, histoire…).

## Règle

Les paroles des chanteurs (Matoub Lounès, Lounis Aït Menguellet, Idir, Slimane Azem…) sont protégées par le droit d'auteur. On n'ajoute ici que des paroles pour lesquelles on a **l'autorisation** des ayants droit (fondation, famille, éditeur, ONDA), ou des textes du **domaine public** (poésie traditionnelle anonyme, poèmes anciens dans une transcription elle-même libre).

Garder la preuve de chaque autorisation dans `licences/` (non versionné).

## Format : `songs.jsonl`, un vers par ligne

```json
{"artist": "…", "title": "…", "year": 1985, "line_no": 1,
 "kab": "vers en kabyle",
 "fr": "traduction française",
 "words": [{"kab": "mot", "fr": "sens", "note": "forme / grammaire"}],
 "hidden_meaning": "sens caché : image, contexte historique ou culturel",
 "licence": "autorisation X du 2026-10-20"}
```

Le serveur charge ce fichier au démarrage : les vers et leurs annotations deviennent des références pour le prof (recherche par mots kabyles et français).

## Qui écrit les annotations

- Traduction et mot-à-mot : linguiste ou enseignant de tamazight.
- Sens caché : idéalement quelqu'un qui connaît l'œuvre de l'artiste (biographes, spécialistes, associations culturelles). Le prof s'appuie sur ces annotations et présente toute autre interprétation comme une lecture possible.
