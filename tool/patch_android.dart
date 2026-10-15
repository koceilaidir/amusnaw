// Prépare le projet Android après `flutter create .` :
//   dart run tool/patch_android.dart
//
// - nom de l'app « Amusnaw », permission Internet (aussi en release),
//   notifications (Android 13+), redémarrage du téléphone (rappel conservé) ;
// - récepteurs de flutter_local_notifications ;
// - ouverture des liens https (url_launcher, page de confidentialité) ;
// - « core library desugaring » exigé par flutter_local_notifications.
//
// Le script peut être relancé sans risque : il ne modifie que ce qui manque.
import 'dart:io';

void main() {
  _patchManifest(File('android/app/src/main/AndroidManifest.xml'));
  final kts = File('android/app/build.gradle.kts');
  final groovy = File('android/app/build.gradle');
  if (kts.existsSync()) {
    _patchGradle(kts, kotlin: true);
  } else if (groovy.existsSync()) {
    _patchGradle(groovy, kotlin: false);
  } else {
    stderr.writeln('build.gradle introuvable : lance d’abord « flutter create . »');
    exitCode = 1;
  }
}

void _patchManifest(File f) {
  if (!f.existsSync()) {
    stderr.writeln('${f.path} introuvable : lance d’abord « flutter create . »');
    exitCode = 1;
    return;
  }
  var s = f.readAsStringSync();
  final before = s;

  s = s.replaceFirst(RegExp(r'android:label="[^"]*"'), 'android:label="Amusnaw"');

  const perms = [
    'android.permission.INTERNET',
    'android.permission.POST_NOTIFICATIONS',
    'android.permission.RECEIVE_BOOT_COMPLETED',
  ];
  for (final p in perms) {
    if (!s.contains('"$p"')) {
      s = s.replaceFirstMapped(RegExp(r'<manifest[^>]*>'),
          (m) => '${m[0]}\n    <uses-permission android:name="$p"/>');
    }
  }

  if (!s.contains('ScheduledNotificationReceiver')) {
    s = s.replaceFirst('</application>', '''
        <receiver android:exported="false"
            android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationReceiver" />
        <receiver android:exported="false"
            android:name="com.dexterous.flutterlocalnotifications.ScheduledNotificationBootReceiver">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED"/>
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED"/>
                <action android:name="android.intent.action.QUICKBOOT_POWERON" />
                <action android:name="com.htc.intent.action.QUICKBOOT_POWERON"/>
            </intent-filter>
        </receiver>
    </application>''');
  }

  if (!s.contains('android:scheme="https"')) {
    const intent = '''
        <intent>
            <action android:name="android.intent.action.VIEW" />
            <data android:scheme="https" />
        </intent>''';
    if (s.contains('<queries>')) {
      s = s.replaceFirst('<queries>', '<queries>$intent');
    } else {
      s = s.replaceFirst('</manifest>', '    <queries>$intent\n    </queries>\n</manifest>');
    }
  }

  if (s != before) {
    f.writeAsStringSync(s);
    stdout.writeln('✓ ${f.path}');
  } else {
    stdout.writeln('= ${f.path} (déjà à jour)');
  }
}

void _patchGradle(File f, {required bool kotlin}) {
  var s = f.readAsStringSync();
  final before = s;
  final flag = kotlin ? 'isCoreLibraryDesugaringEnabled = true' : 'coreLibraryDesugaringEnabled true';
  final dep = kotlin
      ? 'coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")'
      : "coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'";

  if (!s.contains('oreLibraryDesugaringEnabled')) {
    if (s.contains('compileOptions {')) {
      s = s.replaceFirst('compileOptions {', 'compileOptions {\n        $flag');
    } else {
      s = s.replaceFirst(RegExp(r'android\s*\{'), 'android {\n    compileOptions {\n        $flag\n    }');
    }
  }
  if (!s.contains('desugar_jdk_libs')) {
    s = '${s.trimRight()}\n\ndependencies {\n    $dep\n}\n';
  }
  if (s != before) {
    f.writeAsStringSync(s);
    stdout.writeln('✓ ${f.path}');
  } else {
    stdout.writeln('= ${f.path} (déjà à jour)');
  }
}
