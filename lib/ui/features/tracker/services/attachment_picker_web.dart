import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

import 'attachment_picker.dart';

Future<PickedAttachment?> pickAttachment() async {
  final body = web.document.body;
  if (body == null) {
    return null;
  }

  final input = web.HTMLInputElement()
    ..type = 'file'
    ..accept = '*/*';
  body.append(input);

  try {
    input.click();
    final file = await _waitForFileSelection(input);
    if (file == null) {
      return null;
    }
    final normalizedName = file.name.trim();
    if (normalizedName.isEmpty) {
      return null;
    }
    final bytes = await _readBytes(file);
    return PickedAttachment(
      name: normalizedName,
      bytes: bytes,
    );
  } finally {
    input.remove();
  }
}

Future<web.File?> _waitForFileSelection(web.HTMLInputElement input) async {
  await Future.any<void>([
    input.onChange.first,
    input.onError.first,
  ]);
  final files = input.files;
  if (files == null || files.length == 0) {
    return null;
  }
  return files.item(0);
}

Future<Uint8List> _readBytes(web.Blob file) async {
  final reader = web.FileReader()..readAsArrayBuffer(file);
  await reader.onLoadEnd.first;
  final result = (reader.result as JSArrayBuffer?)?.toDart.asUint8List();
  if (result == null) {
    final error = reader.error;
    throw StateError(
      error?.message ?? 'Attachment bytes could not be read from the browser picker.',
    );
  }
  return result;
}
