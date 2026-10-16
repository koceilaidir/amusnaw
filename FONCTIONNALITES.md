# Amusnaw : fonctionnalités et choix techniques

Ce journal est tenu au fil du projet. Il sert de base au PDF de présentation de l'app (fonctionnalités + partie technique). Chaque nouvelle fonctionnalité y est ajoutée.

## 1. Fonctionnalités pour l'utilisateur

### Accueil et compte
- Accueil « Azul. » avec la rosace kabyle (tabzimt) en filigrane.
- **Langue détectée automatiquement** depuis le téléphone, avec un bouton « Changer » (anglais, français, arabe, espagnol, allemand). Le prof explique dans cette langue.
- **Création de compte rapide** : Apple (sur iPhone), Google, e-mail plus tard. Aucun mot de passe stocké.
- Mode « test sans compte » pour la bêta.
- **Reste connecté** : à la réouverture, l'app va directement à l'accueil du jour ; la session se renouvelle à chaque visite (expiration après 90 jours sans ouvrir l'app).

### Réglages
- Langue des explications (envoyée au prof), thème **Automatique / Clair / Sombre**.
- **Rappel quotidien facultatif** à l'heure choisie, message bienveillant dans la langue de l'élève ; conservé après redémarrage du téléphone.
- Politique de confidentialité, déconnexion, **suppression du compte et de toutes les données** (exigée par Google et Apple).

### Le prof IA
- Fait connaissance avec l'élève (niveau, objectifs, vécu : « ma grand-mère parlait kabyle ») et propose des réponses rapides (parler en famille, comprendre les chansons, culture et histoire…).
- **S'appuie sur une base kabyle authentique** (livres traduits, lexiques HCA) au lieu d'inventer.
- **Reste dans son sujet** : refuse poliment le code, les devoirs d'autres matières… et revient à la leçon.
- Pédagogie fondée sur 18 principes (Krashen, Vygotsky, Bloom, Freire, Montessori, répétition espacée de Pimsleur…), voir `docs/PEDAGOGIE.md`.
- **Fait réemployer les mots** vus les jours précédents, en créant des occasions dans la conversation.
- **Réponses affichées mot par mot** pendant qu'elles sont générées, comme ChatGPT.
- **Cartes interactives dans la conversation** : carte du mot (kabyle, Tifinagh, sens), petit exercice à choix, capsule culture. Le prof les demande, mais leur contenu vient de la base vérifiée, jamais de l'IA.
- **Chansons expliquées vers par vers** : mot par mot, sens littéral, puis **sens caché** (images, exil, identité, histoire), à partir de paroles sous licence.

### Progression et motivation
- **Mots appris** : un mot compte quand l'élève l'emploie lui-même, **un autre jour** que celui où il l'a découvert. Message de félicitations avec le nouveau total : « Félicitations ! Ton nombre de mots appris a augmenté : le total est de N ».
- Séance du jour d'environ 8 minutes : révision espacée, nouveauté, dialogue, capsule culture.
- Aucune culpabilisation après une absence (« on reprend en douceur »).
- Exercices avec retour immédiat et bienveillant, une seule erreur corrigée à la fois.
- Capsules culture (Yennayer, Mammeri, Tafsut, Tiwizi, Si Mohand, tabzimt, poterie, Fadhma Aït Mansour…), à lire en entier d'un tap.
- **Mot du jour** différent chaque jour, avec son écriture en Tifinagh (conversion automatique).
- **Révisions espacées** (SM-2) mêlées à la séance du jour : les mots sur le point d'être oubliés reviennent en premier.
- **Programme A1 en 13 unités** (saluer, se présenter, la famille, compter, à table, la maison, le corps, le village, le temps, les verbes, les couleurs, les fêtes), conçu selon la recherche en didactique des langues : 5 mots nouveaux au plus, blocs de langue, reconnaissance puis rappel, révision entrelacée, une capsule culture par unité (références dans `docs/PEDAGOGIE.md`).
- **Le prof suit le programme** : il reçoit l'unité en cours (objectif, mots, blocs, jeu de rôle conseillé) et passe à la suivante quand l'élève a rencontré tous les mots.
- **Leçons générées depuis les lexiques HCA** (animaux marins, mots nouveaux…), avec la source affichée.
- Progression enregistrée sur le téléphone et sur le serveur.
- Parcours A1 → B2 (Tazwara…), compétences (vocabulaire, compréhension, grammaire, culture).

### Design (V2, « le chat d'abord »)
- **L'app s'ouvre toujours sur le chat**, comme Claude ou ChatGPT : « Azul, Koceila. », un rappel des derniers mots vus, puis la question « On apprend, ou on parle d'autre chose ? » avec deux cartes **Apprendre** (leçon du jour, 8 min) et **Discuter** (culture, histoire, chansons), et des idées de sujets sous la saisie.
- **Menu en haut à gauche** : nouvelle conversation, leçons, mot du jour, culture et histoire, progression, **conversations récentes** (gardées sur le téléphone), profil et réglages.
- **Thème en haut à droite** : Automatique / Clair / Sombre et 4 couleurs (terre cuite, ocre, indigo, olivier).
- Bouton « + » de la saisie : raccourcis (leçons, mot du jour, réviser mes mots, culture).
- **Logo** : l'étoile amazighe (itri) redessinée en traits arrondis ; icône d'app blanc cassé sur fond encre.
- **Police Onest** (embarquée dans l'app, fonctionne hors ligne), choisie parce qu'elle affiche tout l'alphabet kabyle (ɛ ɣ ḍ ṭ ẓ ṛ ḥ ṣ č ǧ).
- Interface en français.
- Style iOS (grands titres, listes groupées, barre d'onglets à icônes pleines).
- **Thème clair et sombre** automatique.
- Tons pierre chauds, une seule couleur d'accent, ombres très légères.

## 2. Côté technique

| Brique | Choix |
|---|---|
| App mobile | Flutter (iOS + Android), Material 3 + Cupertino |
| Serveur | FastAPI (Python), Docker Compose, Caddy (HTTPS automatique) |
| Base de données | PostgreSQL |
| IA | Modèle open source auto-hébergé (Qwen 2.5 via Ollama), sans API payante ; serveur compatible OpenAI, donc remplaçable en une ligne par *amusnaw-v1* |
| Connaissances | RAG : recherche BM25 dans le lexique et les phrases alignées, injectées dans le prompt du prof |
| Connexion | Google / Apple : jeton vérifié par le serveur, puis jeton Amusnaw (JWT) |
| Hébergement | VPS Octenium en Algérie (4 cœurs dédiés, 8 Go, 500 Go, Ubuntu 24.04), HTTPS Caddy ; GPU loué pour l'entraînement |
| Temps réel | Réponses en continu (Server-Sent Events) |

### Pipeline de données (livres → base)
- Conversion des **anciennes polices kabyles** des livres HCA (Tira, Tayma, Symbol) vers l'Unicode, police par police.
- **Alignement automatique français ↔ kabyle** des livres traduits (Gale-Church + noms propres et ponctuation, par paragraphes puis par phrases).
- Corpus actuel :
  - **≈ 14 400 mots et termes** (lexiques HCA : vocabulaire moderne, didactique, terre et animaux, animaux marins, juridique, glossaires) + **1 117 prénoms amazighs** avec leur sens ;
  - **45 700 phrases kabyles authentiques** tirées de 43 livres HCA (romans, contes, poésie, histoire, essais) ;
  - **3 235 paires de phrases** français ↔ kabyle (*Le Petit Prince*, *Le fils du pauvre*, *Misère de la Kabylie*) ;
  - fréquence de 97 000 formes kabyles, pour choisir le vocabulaire courant.
- **Page de relecture** pour linguiste (valider / corriger / rejeter, douteux en premier), avec export pour l'entraînement.

### Feuille de route de l'IA
1. MVP : Qwen + base kabyle (RAG).
2. Relecture humaine, plus de livres (objectif : plus de 10 000 paires), dialogues de prof corrigés.
3. Entraînement LoRA sur GPU loué → **amusnaw-v1**, comparé sur un jeu de test avant sa mise en service.
4. Versions suivantes (v2, v3…) avec les nouvelles données.

### Comment fonctionne l'IA d'Amusnaw (comparée à ChatGPT / Claude)

| Étape | ChatGPT / Claude | Amusnaw |
|---|---|---|
| 1. Pré-entraînement | Milliers de milliards de mots, milliers de GPU, coût énorme | Réutilisé : modèle open source Qwen, pré-entraîné par Alibaba |
| 2. Affinage | Dialogues + retours humains | amusnaw-v1 : affinage LoRA sur les livres HCA et des dialogues corrigés par linguiste |
| 3. Produit | Prompt, outils, mémoire | Prompt pédagogique, recherche dans la base kabyle (RAG), suivi des mots appris, filtre hors sujet |

### Architecture « pilotée par le serveur »
L'app rendue au HCA est figée ; toutes les améliorations (prof, leçons, exercices, modèle) se font sur le VPS.
- **Contenus servis par le serveur** : `/content/today` (mot du jour, capsule, leçon), `/content/lessons`, `/content/capsules`. Ajouter une leçon ou une capsule = modifier `server/content/*.json`, sans republier l'app. Hors connexion, l'app garde un contenu de secours.
- **Blocs** : le prof termine sa réponse par une balise (`[[MOT: aman]]`, `[[EXERCICE]]`, `[[CAPSULE: yennayer]]`) ; le serveur la retire et envoie un bloc construit depuis la base vérifiée. Les types de blocs inconnus sont ignorés par l'app : on pourra en ajouter (chanson, carte…) sans casser la version livrée.
- Notifications programmées sur le téléphone (pas de serveur de push).

### Points d'éthique et de droits
- Contenus kabyles relus par des linguistes.
- Livres sources : publications du HCA, utilisées avec l'autorisation du HCA ; les données ne sont pas publiées sur Git.
- Chansons : uniquement avec l'accord des ayants droit.
- Le prof présente ses interprétations (sens caché) comme des lectures possibles.

## 3. À ajouter au fil de l'eau
- (nouvelles fonctionnalités ici)
