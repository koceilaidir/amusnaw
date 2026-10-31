import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

/// Site web : le sélecteur de fichiers du navigateur (sur téléphone, il propose aussi
/// l'appareil photo). La photo est réduite ensuite par le serveur.
Future<Uint8List?> pickPhoto({required bool camera}) {
  final done = Completer<Uint8List?>();
  final input = web.HTMLInputElement()
    ..type = 'file'
    ..accept = 'image/*';

  void finish(Uint8List? bytes) {
    if (!done.isCompleted) done.complete(bytes);
    input.remove();
  }

  Future<void> read(web.File file) async {
    try {
      final buf = await file.arrayBuffer().toDart;
      finish(buf.toDart.asUint8List());
    } catch (e) {
      if (!done.isCompleted) done.completeError(e);
      input.remove();
    }
  }

  input.onchange = ((web.Event _) {
    final file = input.files?.item(0);
    if (file == null) {
      finish(null);
    } else {
      read(file);
    }
  }).toJS;
  input.addEventListener('cancel', ((web.Event _) => finish(null)).toJS);
  // certains navigateurs n'ouvrent le sélecteur que si le champ est dans la page
  input.style.display = 'none';
  web.document.body?.append(input);
  input.click();
  return done.future;
}
