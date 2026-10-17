// Prépare le site web après `flutter create . --platforms web` :
//   dart run tool/patch_web.dart
//
// Titre, description, langue française, couleur olivier, nom de l'app installable.
// Le script peut être relancé sans risque.
import 'dart:io';

const title = 'Amusnaw — apprendre le kabyle';
const description =
    'Amusnaw, un prof IA pour apprendre le kabyle, sa culture et son histoire, un petit pas par jour.';
const olive = '#56662E';

void main() {
  final index = File('web/index.html');
  final manifest = File('web/manifest.json');
  if (!index.existsSync()) {
    stderr.writeln('web/index.html introuvable : lance d’abord « flutter create . --platforms web »');
    exitCode = 1;
    return;
  }
  var s = index.readAsStringSync();
  s = s.replaceFirst(RegExp(r'<html[^>]*>'), '<html lang="fr">');
  s = s.replaceFirst(RegExp(r'<title>.*?</title>', dotAll: true), '<title>$title</title>');
  s = s.replaceFirst(RegExp(r'<meta name="description" content="[^"]*">'),
      '<meta name="description" content="$description">');
  s = s.replaceFirst(RegExp(r'<meta name="apple-mobile-web-app-title" content="[^"]*">'),
      '<meta name="apple-mobile-web-app-title" content="Amusnaw">');
  if (!s.contains('name="theme-color"')) {
    s = s.replaceFirst('</head>', '  <meta name="theme-color" content="$olive">\n</head>');
  }
  // Icônes : logo Amusnaw (fichiers web/favicon.* et web/icons/* fournis avec le projet)
  s = s.replaceFirst(RegExp(r'<link rel="apple-touch-icon"[^>]*>'),
      '<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">');
  if (!s.contains('favicon.ico')) {
    s = s.replaceFirst(RegExp(r'<link rel="icon"[^>]*>'),
        '<link rel="icon" href="favicon.ico" sizes="any">\n  <link rel="icon" type="image/png" href="favicon.png">');
  }
  // Écran de chargement : fond olivier et étoile blanche, comme au lancement de l'app
  if (!s.contains('amusnaw-splash')) {
    s = s.replaceFirst('</head>', '''  <style id="amusnaw-splash">
    html, body { margin: 0; height: 100%; }
    body { background: $olive url("icons/splash-mark.png") no-repeat center / 112px auto; }
  </style>
</head>''');
  }
  index.writeAsStringSync(s);
  stdout.writeln('✓ ${index.path}');

  if (manifest.existsSync()) {
    var m = manifest.readAsStringSync();
    m = m.replaceFirst(RegExp(r'"name":\s*"[^"]*"'), '"name": "Amusnaw"');
    m = m.replaceFirst(RegExp(r'"short_name":\s*"[^"]*"'), '"short_name": "Amusnaw"');
    m = m.replaceFirst(RegExp(r'"description":\s*"[^"]*"'), '"description": "$description"');
    m = m.replaceAllMapped(RegExp(r'"(background_color|theme_color)":\s*"[^"]*"'),
        (x) => '"${x[1]}": "$olive"');
    manifest.writeAsStringSync(m);
    stdout.writeln('✓ ${manifest.path}');
  }
}
