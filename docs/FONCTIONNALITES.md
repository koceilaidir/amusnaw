# Amusnaw : fonctionnalités et choix techniques

Ce journal est tenu au fil du projet. Il sert de base au PDF de présentation de l'app (fonctionnalités + partie technique). Chaque nouvelle fonctionnalité y est ajoutée.

## 1. Fonctionnalités pour l'utilisateur

### Accueil et compte
- Accueil « Azul. » avec la rosace kabyle (tabzimt) en filigrane.
- **Langue détectée automatiquement** depuis le téléphone, avec un bouton « Changer » (anglais, français, arabe, espagnol, allemand). Le prof explique dans cette langue.
- **Création de compte rapide** : Apple (sur iPhone), Google, e-mail plus tard. Aucun mot de passe stocké.
- **« Continuer sans compte »** (prénom seulement), pour la démo et les téléphones sans services Google.
- **Reste connecté** : à la réouverture, l'app va directement à l'accueil du jour ; la session se renouvelle à chaque visite (expiration après 90 jours sans ouvrir l'app).
- **Plein écran** sur téléphone : barre d'état et barre de navigation cachées (un glissement depuis le bord les fait réapparaître).

### Site web
- **La même app dans le navigateur** (Flutter web), servie par le VPS à la même adresse que le prof : ordinateur, tablette ou téléphone, sans rien installer. Mêmes leçons, même prof, mêmes progrès.
- **Mise en page web** : sur ordinateur, menu fixe à gauche (conversations, leçons, culture, progression, réglages) et conversation centrée à largeur de lecture ; accueil en deux panneaux (marque sur fond olivier, connexion à droite). Sur téléphone, la mise en page de l'app.
- Favicon et icônes Amusnaw, écran de chargement olivier.
- Sur le web : « Continuer sans compte » (Google viendra ensuite), pas de rappel quotidien (un navigateur ne programme pas de notification).
- **Limites anti-abus** : 60 messages par heure et par élève, 10 nouveaux comptes par heure et par connexion ; l'élève reçoit un message bienveillant (« fais une petite pause »).

### Réglages
- Langue des explications (envoyée au prof), thème **Automatique / Clair / Sombre**.
- **Rappel quotidien facultatif** à l'heure choisie, message bienveillant dans la langue de l'élève ; conservé après redémarrage du téléphone.
- Politique de confidentialité, déconnexion, **suppression du compte et de toutes les données** (exigée par Google et Apple).

### Le prof IA
- Fait connaissance avec l'élève (niveau, objectifs, vécu : « ma grand-mère parlait kabyle ») et propose des réponses rapides.
- **Ne jamais inventer de kabyle** : les réponses exactes sont écrites par le serveur à partir de la base, le modèle ne sert qu'à la conversation libre.
  - **« Comment on dit … ? » / « Que veut dire … ? »** : réponse tirée des lexiques HCA, avec la source ; si le mot manque, le prof le dit honnêtement.
  - **« Conjugue … »** : tableau complet (passé, négation, futur, habitude) pour **6 346 verbes** : règles de K. Bouamara (180 formes de référence reproduites sans erreur) et tables de conjugaison libres (amyag.com via taqbaylit/kabyle-verbs), croisées forme par forme.
  - **Analyse des formes** : « Que veut dire yeswa ? » → « forme du verbe sew (boire), au passé, il » ; « temdint » → forme annexée de « tamdint » (ville) ; pronoms collés expliqués (« uqerru-iw » : -iw = mon) ; pluriels et féminins reconnus grâce au correcteur orthographique kabyle.
  - **Autres sens** : quand un mot a plusieurs sens selon les sources, le prof les donne (« takerrust » : « complexe » dans le lexique HCA, « voiture » dans l'usage courant appris sur Tatoeba, à valider).
  - **Noms de lieux** : 5 344 villes et villages en kabyle (« Oran » → « Wehran »), d'OpenStreetMap.
  - **Sens en anglais** quand le sens français manque encore (3 682 sens appris sur Tatoeba, 29 977 termes modernes des logiciels libres), toujours présenté comme tel.
  - **12 fiches de grammaire** (état d'annexion, fell-ak / fell-am, possessifs, négation ur … ara, futur, pluriel, prononciation…), et correction bienveillante de fautes fréquentes (« tellid » → « telliḍ »).
  - **Contrôle qualité** : tout kabyle cité par le modèle est vérifié (mot attesté ou forme analysable) ; le kabyle inventé est signalé dans les journaux.
- **Reste dans son sujet** : refuse poliment le code, les devoirs d'autres matières, les conseils médicaux, juridiques ou financiers, et revient à la leçon.
- Pédagogie fondée sur 18 principes (Krashen, Vygotsky, Bloom, Freire, Montessori, répétition espacée de Pimsleur…), voir `docs/PEDAGOGIE.md`.
- **Fait réemployer les mots** vus les jours précédents, en créant des occasions dans la conversation.
- **Réponses affichées mot par mot** pendant qu'elles sont générées.
- **Cartes interactives dans la conversation** : carte du mot (kabyle, Tifinagh, sens), petit exercice à choix, capsule culture. Le prof les demande, mais leur contenu vient de la base vérifiée, jamais de l'IA.
- **Chansons expliquées vers par vers** : mot par mot, sens littéral, puis **sens caché**, à partir de paroles sous licence.

### Progression et motivation
- **Mots appris** : un mot compte quand l'élève l'emploie lui-même, **un autre jour** que celui où il l'a découvert.
- Séance du jour d'environ 8 minutes : révision espacée, nouveauté, dialogue, capsule culture.
- Aucune culpabilisation après une absence (« on reprend en douceur »).
- Exercices avec retour immédiat et bienveillant, une seule erreur corrigée à la fois.
- Capsules culture (Yennayer, Mammeri, Tafsut, Tiwizi, Si Mohand, tabzimt, poterie, Fadhma Aït Mansour…).
- **Mot du jour** différent chaque jour, avec son écriture en Tifinagh (conversion automatique).
- **Révisions espacées** (SM-2) mêlées à la séance du jour.
- **Programme A1 en 13 unités** (5 mots nouveaux au plus, blocs de langue, reconnaissance puis rappel, révision entrelacée, une capsule culture par unité ; références dans `docs/PEDAGOGIE.md`).
- **Le prof suit le programme** et passe à l'unité suivante quand l'élève a rencontré tous les mots.

### Design (V2, « le chat d'abord »)
- **L'app s'ouvre toujours sur le chat** : « Azul, Koceila. », puis « On apprend, ou on parle d'autre chose ? » avec deux cartes **Apprendre** et **Discuter** ; le clavier ne s'ouvre qu'au toucher.
- **Menu en haut à gauche** (nouvelle conversation, leçons, mot du jour, culture, progression, conversations récentes, réglages), **thème en haut à droite** (Automatique / Clair / Sombre).
- Couleur principale unique : **vert olivier** (#56662E), aussi pour l'icône de l'app et les boutons.
- **Logo** : l'étoile amazighe (itri) en traits arrondis. **Police Onest** (affiche tout l'alphabet kabyle : ɛ ɣ ḍ ṭ ẓ ṛ ḥ ṣ č ǧ). Interface en français.

## 2. Côté technique

| Brique | Choix |
|---|---|
| App mobile et site web | Flutter (iOS, Android, navigateur), Material 3 + Cupertino ; site servi par Caddy à la même adresse que l'API |
| Serveur | FastAPI (Python), Docker Compose, Caddy (HTTPS automatique) |
| Base de données | PostgreSQL |
| IA | Modèle open source auto-hébergé (Qwen 2.5 via Ollama), sans API payante ; remplaçable par *amusnaw-v1* |
| Connaissances | RAG (BM25) + **aiguilleur** qui répond sans le modèle (vocabulaire, conjugaison, analyse des formes, grammaire, hors sujet) |
| Langue | Conjugueur à règles (K. Bouamara, 2026), lemmatiseur kabyle (verbes, état d'annexion, pluriels, pronoms collés) |
| Connexion | Google / Apple : jeton vérifié par le serveur, puis jeton Amusnaw (JWT) |
| Hébergement | VPS Octenium en Algérie (4 cœurs, 8 Go), HTTPS Caddy |
| Temps réel | Réponses en continu (Server-Sent Events) |

### Pipeline de données (livres → base), reconstruit d'un seul script (`data_pipeline/rebuild_all.sh`)
1. **Corpus** : 43 livres HCA ; anciennes polices kabyles converties en Unicode ; restes corrigés ($ → ɣ, £ → Ɣ…) ; **autres variantes exclues** (chaoui, touareg, mozabite…) ; poésie découpée par strophe.
2. **Lexiques HCA** : vocabulaire moderne, didactique, rhétorique, terre et animaux, animaux marins, juridique, prénoms, corps humain (transcrit du scan), expressions (*Tinfaliyin*, 5 818 expressions traduites), glossaires de fin de livres.
3. **Verbes** : 6 346 verbes (règles de Bouamara + tables libres + verbes attestés dans les livres HCA et dans Tatoeba + verbes découverts automatiquement après « ad »).
4. **Lemmatiseur** : chaque forme ramenée à son mot de base (270 600 formes connues) ; **90,3 % des mots du corpus reconnus**.
5. **Livres traduits alignés par les mots, pas « en miroir »** (*Le Petit Prince*, *Le fils du pauvre*, *Misère de la Kabylie*) : concordance des lemmes kabyles et des racines françaises ; paires décalées repérées et écartées (≈ 2 660 paires fiables ; décalages : 6,4 % Camus, 10,5 % Feraoun, 1,8 % Petit Prince).
6. **Apprentissage de traductions** sur ces paires et sur 226 000 phrases Tatoeba kabyle-français (**3 221 mots**, à valider ; test caché 74 % strict, ≈ 90 % à la relecture) et vers l'anglais (3 682 sens, ≈ 95 % à la relecture). Un sens appris n'est jamais préféré à un sens HCA.
7. **Ressources libres** : Tatoeba (226 000 paires kabyle-français, 758 000 phrases kabyles), contes Numidya, Wikipédia en kabyle (5 600 articles), Common Voice (168 000 phrases), toponymes OpenStreetMap, tables de verbes, correcteur Hunspell, lexique de mathématiques Tafsut, mémoire de traduction des logiciels libres.

Chiffres : ≈ 41 400 phrases kabyles HCA + 3 742 strophes + 12 400 passages de Wikipédia ; plus de 1,2 million de phrases kabyles servent de preuves d'usage ; ≈ 24 000 mots et termes avec sens français ; ≈ 70 000 paires kabyle ↔ français citables (livres traduits, expressions, Bouamara, Tatoeba, contes) ; 1 117 prénoms ; 5 344 noms de lieux.

- **Page de relecture** pour linguiste (valider / corriger / rejeter, douteux en premier), avec export pour l'entraînement.
- **Jeu de test de 36 questions** (`server/eval/`) : 23 sont désormais traitées sans le modèle.

### Feuille de route de l'IA
1. MVP : Qwen + base kabyle (RAG) + aiguilleur et garde-fous (fait).
2. Relecture humaine, plus de livres, dialogues de prof corrigés.
3. Entraînement LoRA sur GPU loué → **amusnaw-v1**, comparé sur le jeu de test avant sa mise en service. Les garde-fous restent en place.

### Architecture « pilotée par le serveur »
L'app rendue au HCA est figée ; toutes les améliorations (prof, leçons, exercices, verbes, fiches de grammaire, modèle) se font sur le VPS.
- **Contenus servis par le serveur** : `/content/today`, `/content/lessons`, `/content/capsules` ; `server/content/*.json` (programme, verbes, fiches de grammaire, mots-outils).
- **Blocs** : le prof termine sa réponse par une balise (`[[MOT: aman]]`, `[[EXERCICE]]`, `[[CAPSULE: yennayer]]`) ; le serveur envoie un bloc construit depuis la base vérifiée.

### Points d'éthique et de droits
- Contenus kabyles relus par des linguistes ; tout ce qui est appris ou découvert automatiquement est marqué « à valider ».
- Livres sources : publications du HCA, utilisées avec l'autorisation du HCA ; les données ne sont pas publiées sur Git.
- Sources sous licence libre citées : K. Bouamara (HAL, CC BY-NC-SA pour la conjugaison ; CC BY-NC-ND pour le corpus par niveaux : cité tel quel, app non commerciale, pas d'entraînement).
- Ressources libres citées avec leur licence : Tatoeba (CC0 / CC BY 2.0 FR), contes Numidya (CC BY-NC 4.0), Wikipédia (CC BY-SA 4.0), Common Voice (CC0), OpenStreetMap (ODbL), Hunspell kabyle (MIT), KabLex / Tafsut (CC BY 4.0), traductions de logiciels libres (CC BY 4.0), tables de verbes taqbaylit/kabyle-verbs (CC BY 4.0 déclarée ; **contenu issu d'amyag.com : accord de l'auteur du site à confirmer avant la publication**).
- Non intégrés : traductions du Coran et de la Bible (sensibilité, droits des traductions). Faute de droits : dictionnaire de Dallet, mémoires universitaires, Assimil, Naït-Zerrad, Mammeri (Maspero), etc.
- Chansons : uniquement avec l'accord des ayants droit.
