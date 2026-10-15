# Tester Amusnaw sur ton téléphone (ce soir)

Le serveur tourne sur ton PC, le téléphone s'y connecte par le Wi-Fi.
Il faut : Docker Desktop, Flutter, et le téléphone sur le **même Wi-Fi** que le PC.

## 1. Lancer le serveur sur le PC

Dans un terminal, dossier `amusnaw\server` :

```bash
docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml exec ollama ollama pull modelscope.cn/Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_K_M
```

Le second ordre télécharge le modèle (~2 Go, une seule fois) depuis **ModelScope**, le miroir chinois :
le registre officiel d'Ollama passe par Cloudflare, inaccessible depuis la Chine.
Hors de Chine : `ollama pull qwen2.5:3b`, puis lance le serveur avec `$env:LLM_MODEL="qwen2.5:3b"` avant `docker compose … up -d`.

### Depuis la Chine : Flutter

`flutter pub get` échoue (« TLS error … pub.dev ») car pub.dev est bloqué. Utilise le miroir officiel chinois, dans PowerShell :

```powershell
$env:PUB_HOSTED_URL="https://pub.flutter-io.cn"
$env:FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"
flutter pub get
```

Pour ne plus avoir à le refaire : Paramètres Windows → « Modifier les variables d'environnement » → ajoute ces deux variables à ton compte.
Vérifie : http://localhost:8000/health doit afficher `"knowledge_items": 3711` environ.

## 2. Trouver l'adresse IP du PC

```bash
ipconfig
```
Note l'« Adresse IPv4 » de ta carte Wi-Fi, par ex. `192.168.1.23`.

Si le téléphone n'arrive pas à joindre le PC : autorise le port 8000 dans le pare-feu Windows
(Pare-feu Windows → Paramètres avancés → Règles de trafic entrant → Nouvelle règle → Port TCP 8000).

## 3. Lancer l'app

Dans `amusnaw` (la première fois seulement : `flutter create .`, `flutter pub get`, `dart run tool/patch_android.dart`, `dart run flutter_launcher_icons` ; après chaque mise à jour du code : `flutter pub get` et `dart run tool/patch_android.dart`) :

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.23:8000
```

Sur l'écran d'accueil, touche **« Test without an account »**, donne un prénom : tu arrives dans le chat avec le prof.

- **Android** : le HTTP local est déjà autorisé en debug (`android/app/src/debug/AndroidManifest.xml`).
- **iPhone** : il faut un Mac avec Xcode. Ajoute dans `ios/Runner/Info.plist` :
  ```xml
  <key>NSAppTransportSecurity</key>
  <dict><key>NSAllowsArbitraryLoads</key><true/></dict>
  ```
  (à retirer avant publication : en production l'API est en HTTPS).

## 4. Page de relecture

http://localhost:8000/review — code : `kabyle`.
Les paires douteuses apparaissent en premier. Ce qui est rejeté n'est plus proposé au prof ; ce qui est validé est mis en avant.
Export pour l'entraînement : bouton du navigateur sur http://localhost:8000/review/export.jsonl (avec le code dans l'en-tête — ou depuis le terminal :
`curl -H "X-Review-Token: kabyle" http://localhost:8000/review/export.jsonl -o valide.jsonl`).

## Ce qu'il faut savoir pendant le test

- Sans GPU, le modèle 3B répond en quelques secondes ; son kabyle reste faible. Le prof s'appuie sur ta base (livres) quand il trouve des phrases liées au message.
- La base marche mieux avec des messages en **français** (les livres sont alignés avec le français). En anglais, elle ne trouve que les mots kabyles cités.
- Les écrans Today / Exercice / Progress utilisent encore le contenu de démo.
