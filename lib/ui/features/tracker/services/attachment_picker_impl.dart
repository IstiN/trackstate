import 'package:file_selector/file_selector.dart';

import 'attachment_picker.dart';

Future<PickedAttachment?> pickAttachment() async {
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
