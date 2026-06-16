import 'dart:typed_data';

import 'attachment_picker_impl.dart'
    if (dart.library.js_interop) 'attachment_picker_web.dart' as impl;

class PickedAttachment {
  const PickedAttachment({required this.name, required this.bytes});

  final String name;
  final Uint8List bytes;

  int get sizeBytes => bytes.length;
}

typedef AttachmentPicker = Future<PickedAttachment?> Function();

Future<PickedAttachment?> pickAttachmentWithFileSelector() =>
    impl.pickAttachment();
