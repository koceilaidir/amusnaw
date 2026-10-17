// Prépare le projet Android après `flutter create .` :
//   dart run tool/patch_android.dart
//
// - nom de l'app « Amusnaw », permission Internet (aussi en release),
//   notifications (Android 13+), redémarrage du téléphone (rappel conservé) ;
// - récepteurs de flutter_local_notifications ;
// - ouverture des liens https (url_launcher, page de confidentialité) ;
// - « core library desugaring » exigé par flutter_local_notifications ;
// - identifiant de l'app « com.amusnaw.app » (celui déclaré chez Google) ;
// - signature de la version finale avec la clé décrite dans android/key.properties
//   (voir docs/PUBLIER_ANDROID.md) ; sans ce fichier, la clé de debug reste utilisée.
//
// Le script peut être relancé sans risque : il ne modifie que ce qui manque.
import 'dart:io';

const appId = 'com.amusnaw.app';

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

  // Identifiant de l'app (le « namespace » du code Kotlin ne change pas)
  s = s.replaceFirst(RegExp(r'applicationId\s*=?\s*"[^"]*"'),
      kotlin ? 'applicationId = "$appId"' : 'applicationId "$appId"');

  // Signature de la version finale
  if (!s.contains('key.properties')) {
    if (kotlin) {
      s = '''import java.io.FileInputStream
import java.util.Properties

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
}

$s''';
      s = s.replaceFirst(RegExp(r'android\s*\{'), '''android {
    signingConfigs {
        create("release") {
            if (keystorePropertiesFile.exists()) {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }''');
      s = s.replaceFirst('signingConfig = signingConfigs.getByName("debug")',
          'signingConfig = if (keystorePropertiesFile.exists()) signingConfigs.getByName("release") '
          'else signingConfigs.getByName("debug")');
    } else {
      s = s.replaceFirst(RegExp(r'android\s*\{'), '''def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    signingConfigs {
        release {
            if (keystorePropertiesFile.exists()) {
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
            }
        }
    }''');
      s = s.replaceFirst('signingConfig signingConfigs.debug',
          'signingConfig keystorePropertiesFile.exists() ? signingConfigs.release : signingConfigs.debug');
    }
  }
  if (s != before) {
    f.writeAsStringSync(s);
    stdout.writeln('✓ ${f.path}');
  } else {
    stdout.writeln('= ${f.path} (déjà à jour)');
  }
}
