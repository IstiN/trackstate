import 'dart:typed_data';

import 'package:url_launcher/url_launcher.dart';

Future<bool> launchAttachmentDownload(
  Uint8List bytes, {
  required String fileName,
  String? mediaType,
}) {
  final uri = mediaType == null
      ? Uri.dataFromBytes(bytes, parameters: {'name': fileName})
      : Uri.dataFromBytes(
          bytes,
          mimeType: mediaType,
          parameters: {'name': fileName},
        );
  return launchUrl(uri, webOnlyWindowName: '_blank');
}
