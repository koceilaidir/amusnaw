# Version finale Android (APK pour le HCA)

Trois étapes, dans l'ordre : la clé de signature, Google, puis l'APK.
Tout se fait sur le PC, dans le dossier `amusnaw`. Depuis la Chine, la console Google demande un VPN.

## 1. Créer la clé de signature (une seule fois, à garder précieusement)

Cette clé « signe » l'app. **Si elle est perdue, il n'est plus possible de publier une mise à jour de la même app.**
Garde une copie du fichier `.jks` et des mots de passe hors du PC (clé USB, gestionnaire de mots de passe).

Dans PowerShell (`keytool` est fourni avec Android Studio) :

```powershell
& "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" -genkey -v `
  -keystore C:\Users\Lenovo\amusnaw-release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias amusnaw
```

Il demande un mot de passe, puis ton nom et ton organisation (« Amusnaw », « DZ »…).

Crée ensuite le fichier `android\key.properties` (il n'est jamais envoyé sur Git) :

```properties
storePassword=LE_MOT_DE_PASSE
keyPassword=LE_MOT_DE_PASSE
keyAlias=amusnaw
storeFile=C:/Users/Lenovo/amusnaw-release.jks
```

Puis : `dart run tool/patch_android.dart`. Le script règle l'identifiant de l'app (`com.amusnaw.app`) et la signature.

Relève l'empreinte **SHA-1** de la clé (Google en a besoin) :

```powershell
& "C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe" -list -v `
  -keystore C:\Users\Lenovo\amusnaw-release.jks -alias amusnaw
```

## 2. Connexion Google (console.cloud.google.com)

1. Crée un projet « Amusnaw ».
2. **Écran de consentement OAuth** : type « Externe », nom « Amusnaw », adresse de contact, lien vers la politique de confidentialité, puis « Publier l'application » (sinon seuls les testeurs déclarés peuvent se connecter).
3. **Identifiants → Créer un ID client OAuth**, deux fois :
   - type **Application Web**, nom « Amusnaw serveur ». Son identifiant (`….apps.googleusercontent.com`) sert au serveur **et** à l'app ;
   - type **Android**, nom de package `com.amusnaw.app`, empreinte SHA-1 de l'étape 1. Rien à recopier : Google reconnaît l'app à sa signature.
   - Pour tester aussi en mode debug : un second ID Android avec le SHA-1 de la clé de debug (`keytool -list -v -keystore %USERPROFILE%\.android\debug.keystore -alias androiddebugkey -storepass android`).
4. Sur le VPS, dans `/opt/amusnaw/server/.env` :
   ```
   GOOGLE_CLIENT_IDS=<ID client Web>
   DEV_LOGIN=true
   CONTACT_EMAIL=<adresse de contact dédiée, ex. contact@…>
   ```
   `CONTACT_EMAIL` s'affiche dans la politique de confidentialité (`/privacy`), exigée par Google.
   `DEV_LOGIN=true` garde le bouton « Continuer sans compte » (prénom seulement) : utile pour la démo, et pour les téléphones sans services Google (Huawei récents, téléphones chinois). Puis : `docker compose up -d api`.

## 3. Construire l'APK

```powershell
flutter build apk --release `
  --dart-define=API_BASE_URL=https://5-39-119-109.sslip.io `
  --dart-define=GOOGLE_SERVER_CLIENT_ID=<ID client Web> `
  --dart-define=TEST_LOGIN=true
```

(`API_BASE_URL` = l'adresse `API_DOMAIN` du VPS.) Le fichier est dans `build\app\outputs\flutter-apk\app-release.apk`. Pour le Play Store plus tard : `flutter build appbundle` avec les mêmes options.

## 4. Vérifier avant de remettre l'APK

- [ ] Installer l'APK sur un téléphone **où l'ancienne version de test a été désinstallée** (signature différente).
- [ ] « Continuer avec Google » : le compte s'affiche, on arrive au chat.
- [ ] « Continuer sans compte » fonctionne.
- [ ] Plein écran, mode sombre, rappel quotidien, page de confidentialité (adresse de contact renseignée).
- [ ] Une séance complète, une conjugaison, « Que veut dire … ? ».
- [ ] Réglages → supprimer le compte : le compte disparaît bien.

Si Google répond « erreur 10 » (`DEVELOPER_ERROR`) : le SHA-1 ou le nom de package déclaré dans la console ne correspond pas à l'APK installé.
