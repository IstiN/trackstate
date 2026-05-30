import 'dart:typed_data';

import 'attachment_download_launcher_stub.dart'
    if (dart.library.js_interop) 'attachment_download_launcher_web.dart'
    as impl;

Future<bool> launchAttachmentDownload(
  Uint8List bytes, {
  required String fileName,
  String? mediaType,
}) => impl.launchAttachmentDownload(
  bytes,
  fileName: fileName,
  mediaType: mediaType,
);
