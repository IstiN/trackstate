@JS()
library;

import 'dart:convert';
import 'dart:js_interop';

import 'package:web/web.dart' as web;

Future<Object?> fetchGitHubAuthProbeJson(
  Uri uri, {
  required Map<String, String> headers,
  Object? client,
}) async {
  final requestHeaders = web.Headers();
  headers.forEach((key, value) {
    requestHeaders.set(key, value);
  });
  final response = await web.window.fetch(
    uri.toString().toJS,
    web.RequestInit(
      method: 'GET',
      headers: requestHeaders,
    ),
  ).toDart;
  return jsonDecode((await response.text().toDart).toDart);
}
