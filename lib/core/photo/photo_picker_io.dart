import 'package:flutter/foundation.dart' show Uint8List;
import 'package:image_picker/image_picker.dart';

/// Téléphone : appareil photo ou galerie, photo déjà réduite (envoi plus rapide).
Future<Uint8List?> pickPhoto({required bool camera}) async {
  final file = await ImagePicker().pickImage(
    source: camera ? ImageSource.camera : ImageSource.gallery,
    maxWidth: 1280,
    maxHeight: 1280,
    imageQuality: 85,
  );
  return file?.readAsBytes();
}
