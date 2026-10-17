# Site web Amusnaw

Le site est **la même app Flutter**, construite pour le navigateur. Il est servi par le VPS à la même adresse que l'API (Caddy envoie `/auth`, `/tutor`, `/content`… au serveur, et tout le reste au site). Il n'y a donc pas de réglage CORS, et chaque mise à jour du prof, des leçons ou de la base profite au site comme à l'app.

## 1. Préparer (une seule fois, sur le PC, dossier `amusnaw`)

```powershell
flutter create . --platforms web
dart run tool/patch_web.dart
flutter pub get
```

## 2. Construire

```powershell
flutter build web --release --no-web-resources-cdn `
  --dart-define=API_BASE_URL=https://5-39-119-109.sslip.io
```

`--no-web-resources-cdn` : le moteur d'affichage est servi par le VPS et pas par les serveurs de Google. Sans cette option, le site ne s'ouvre pas depuis la Chine.

Le site est dans `build\web`.

## 3. Mettre en ligne

```powershell
scp -r build\web\* root@5.39.119.109:/opt/amusnaw/server/web/
```

Puis sur le VPS (une seule fois, après le `git pull` qui apporte le nouveau `Caddyfile`) :

```bash
cd /opt/amusnaw/server
chmod -R a+rX web
grep -q '^DEV_LOGIN=true' .env || echo "DEV_LOGIN=true" >> .env   # « Continuer sans compte »
docker compose up -d api caddy
```

Le site s'ouvre à l'adresse `https://5-39-119-109.sslip.io`. Pour les mises à jour suivantes, refaire seulement les étapes 2 et 3 (pas besoin de relancer Caddy).

## Ce qui change par rapport à l'app

- **Connexion** : « Continuer sans compte » (prénom seulement). La connexion Google sur le web demande le bouton officiel de Google : elle viendra ensuite, avec l'identifiant client « Web ».
- **Pas de rappel quotidien** : un navigateur ne peut pas programmer de notification ; la rubrique est masquée dans les réglages.
- Tout le reste est identique : prof en continu (mot par mot), leçons, mot du jour, capsules, progression, thème clair / sombre.

## Plus tard

- Un vrai nom de domaine (par exemple `amusnaw.dz` ou un sous-domaine du HCA) : changer `API_DOMAIN` dans `.env` et `API_BASE_URL` au moment du build. Caddy crée le certificat HTTPS tout seul.
- Limiter le nombre de messages par visiteur : un site public peut recevoir beaucoup de visites, et le modèle tourne sur le processeur du VPS.
