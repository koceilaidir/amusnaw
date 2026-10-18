# Nom de domaine et connexion par e-mail (Brevo)

L'élève tape son adresse e-mail, reçoit un **code à 6 chiffres**, le tape dans l'app : il est connecté. Il n'y a aucun mot de passe à retenir ni à stocker. Le compte est créé à la première connexion, et le même e-mail retrouve ensuite le même compte et la même progression, sur le site comme sur l'app.

Le code est prêt côté serveur et côté app. Le bouton « Continuer avec un e-mail » apparaît tout seul dès que Brevo est configuré.

## 1. Nom de domaine → VPS

Chez le registraire (ex. `amusnaw.com`), crée deux enregistrements DNS :

| Type | Nom | Valeur |
|---|---|---|
| A | `@` | `5.39.119.109` |
| A | `www` | `5.39.119.109` |

Puis sur le VPS, dans `/opt/amusnaw/server/.env` :

```
API_DOMAIN=amusnaw.com
```

Relance Caddy avec `docker compose up -d caddy`. Le certificat HTTPS est créé automatiquement, en une minute environ, une fois le DNS propagé.

Reconstruis ensuite le site avec la nouvelle adresse :

```powershell
flutter build web --release --no-web-resources-cdn --dart-define=API_BASE_URL=https://amusnaw.com
scp -r build\web root@5.39.119.109:/opt/amusnaw/server/
```

## 1b. Google Cloud (à mettre à jour avec le domaine)

Console Google Cloud → projet Amusnaw :
- **Identifiants → ID client « Application Web » → Origines JavaScript autorisées** : ajoute `https://amusnaw.com` (garde l'ancienne adresse sslip.io le temps de la transition).
- **Google Auth Platform → Branding** :
  - Logo : `assets/icon/amusnaw-logo-120.png` (120 × 120). Ajouter un logo déclenche une vérification par Google (quelques jours).
  - Page d'accueil : `https://amusnaw.com`
  - Règles de confidentialité : `https://amusnaw.com/privacy`
  - Domaines autorisés : `amusnaw.com`
- Puis reconstruis le site avec `API_BASE_URL=https://amusnaw.com` (même ID client Google).

## 2. Brevo

1. Crée un compte sur brevo.com. L'offre gratuite permet 300 e-mails par jour.
2. **Expéditeurs, domaines et IP dédiées → Domaines → Ajouter un domaine** : `amusnaw.com`. Brevo affiche des enregistrements DNS (TXT `brevo-code`, DKIM, et DMARC conseillé) : ajoute-les chez le registraire, puis clique sur « Vérifier ». Sans cela, les codes arrivent dans les spams.
3. **Expéditeurs → Ajouter** : `bonjour@amusnaw.com`, nom « Amusnaw ».
4. **SMTP et API → Clés API → Générer une clé** : copie-la (elle commence par `xkeysib-`).

Puis sur le VPS, dans `.env` :

```
BREVO_API_KEY=xkeysib-…
MAIL_FROM=bonjour@amusnaw.com
MAIL_FROM_NAME=Amusnaw
CONTACT_EMAIL=bonjour@amusnaw.com
```

Applique avec `docker compose up -d api`.

Pour vérifier que c'est actif, ouvre `https://amusnaw.com/auth/methods`. La réponse doit contenir `"email": true`.

## Sécurité

- Le code est valable 15 minutes, avec 5 essais au maximum. Le serveur n'enregistre qu'une empreinte du code, jamais le code lui-même.
- Une même adresse ne peut pas recevoir plus de 5 codes par heure, et une même connexion pas plus de 20 demandes par heure.
- La clé Brevo ne quitte jamais le serveur : elle est dans `.env`, qui n'est pas dans Git.
