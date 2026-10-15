# Amusnaw

Application mobile Flutter : un prof IA qui apprend le kabyle (écriture latine), sa culture et son histoire, dans la langue de l'utilisateur. Thème clair/sombre automatique, style iOS.

## App mobile

Les dossiers natifs Android/iOS ne sont pas encore générés. Dans ce dossier :

```bash
flutter create . --org dz.amusnaw --project-name amusnaw --platforms android,ios
flutter pub get
dart run tool/patch_android.dart      # nom, permissions, notifications (relançable sans risque)
dart run flutter_launcher_icons        # icône ⵣ
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=GOOGLE_SERVER_CLIENT_ID=xxxx.apps.googleusercontent.com
```

`flutter create .` ne remplace pas les fichiers existants de `lib/`.

### Connexion Google / Apple — configuration à faire une fois

- **Google** : dans Google Cloud Console, créer des identifiants OAuth « Web » (son ID = `GOOGLE_SERVER_CLIENT_ID`), « Android » (avec l'empreinte SHA-1) et « iOS ». Sur iOS, ajouter le *reversed client ID* dans `ios/Runner/Info.plist` (voir la doc du package `google_sign_in`).
- **Apple** : dans le compte Apple Developer, activer *Sign in with Apple* pour le bundle ID, puis dans Xcode ajouter la capability *Sign in with Apple*. Le bouton Apple n'apparaît que sur iOS (obligatoire sur l'App Store dès qu'on propose Google).

## Serveur (VPS, Docker)

```
server/
  docker-compose.yml   Postgres + API (FastAPI) + Caddy (HTTPS auto) + Ollama (optionnel)
  .env.example         variables à copier dans .env
  api/                 code de l'API
  prompts/             prompt système du prof
```

Sur le VPS (Docker installé, domaine pointé vers le serveur) :

```bash
cd server
cp .env.example .env        # remplir les valeurs
docker compose up -d --build
# modèle open source local, sans API payante :
docker compose --profile llm up -d
docker compose exec ollama ollama pull qwen2.5:7b
```

Routes : `POST /auth/google`, `POST /auth/apple` (échangent le jeton du fournisseur contre un jeton Amusnaw), `GET /me`, `PATCH /me/language`, `POST /tutor/chat`, `GET /health`.

Le prof parle à n'importe quel serveur compatible OpenAI (`LLM_BASE_URL`) : Ollama au départ, puis nos propres modèles entraînés (servis par vLLM) sans changer le code.

## Structure de l'app

```
lib/
  main.dart                 thème clair/sombre (suit le téléphone), langue
  theme/                    palette iOS, typo Noto/Tifinagh, rosace tabzimt
  core/locale/              langue détectée depuis le téléphone + choix
  core/auth/                connexion Google / Apple
  core/learning/            répétition espacée (SM-2), suivi de l'apprenant
  core/api/                 appels authentifiés vers le serveur
  content/                  contenu de démo (à faire valider par un linguiste)
  widgets/                  composants iOS partagés
  features/
    onboarding/             1 · accueil, langue, connexion
    tutor/                  2 · chat avec le prof
    today/                  3 · séance du jour
    exercise/               4 · exercices + capsule culture
    progress/               5 · progression
    learn/                  liste des leçons
    home/                   barre d'onglets
docs/PEDAGOGIE.md           charte pédagogique du prof
```

En mode debug, « Use email instead » entre directement dans l'app : pratique pour tester les écrans sans serveur ni comptes Google/Apple. Le chat avec le prof, lui, a besoin du serveur.
