import 'dart:typed_data';

import 'package:file_selector/file_selector.dart';

class PickedAttachment {
  const PickedAttachment({required this.name, required this.bytes});

  final String name;
  final Uint8List bytes;

  int get sizeBytes => bytes.length;
}

typedef AttachmentPicker = Future<PickedAttachment?> Function();

Future<PickedAttachment?> pickAttachmentWithFileSelector() async {
  final file = await openFile();
  if (file == null) {
    return null;
  }

  final normalizedName = file.name.trim();
  if (normalizedName.isEmpty) {
    return null;
  }

  return PickedAttachment(
    name: normalizedName,
    bytes: await file.readAsBytes(),
  );
}
