import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

Future<bool> launchAttachmentDownload(
  Uint8List bytes, {
  required String fileName,
  String? mediaType,
}) async {
  final body = web.document.body;
  if (body == null) {
    return false;
  }
  final blob = mediaType == null
      ? web.Blob(<JSUint8Array>[bytes.toJS].toJS)
      : web.Blob(
          <JSUint8Array>[bytes.toJS].toJS,
          web.BlobPropertyBag(type: mediaType),
        );
  final objectUrl = web.URL.createObjectURL(blob);
  final anchor = web.HTMLAnchorElement()
    ..href = objectUrl
    ..download = fileName
    ..style.position = 'absolute'
    ..style.left = '-9999px'
    ..style.width = '1px'
    ..style.height = '1px'
    ..style.opacity = '0';
  body.append(anchor);
  anchor.click();
  unawaited(
    Future<void>.delayed(const Duration(seconds: 1), () {
      anchor.remove();
      web.URL.revokeObjectURL(objectUrl);
    }),
  );
  return true;
}
