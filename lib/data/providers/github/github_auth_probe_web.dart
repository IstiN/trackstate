@JS()
library;

import 'dart:js_interop';

import 'package:web/web.dart' as web;

class GitHubAuthProbeResponse {
  const GitHubAuthProbeResponse({required this.statusCode, required this.body});

  final int statusCode;
  final String body;
}

Future<GitHubAuthProbeResponse> fetchGitHubAuthProbeResponse(
  Uri uri, {
  required Map<String, String> headers,
  Object? client,
}) async {
  final requestHeaders = web.Headers();
  headers.forEach((key, value) {
    requestHeaders.set(key, value);
  });
  final response = await web.window
      .fetch(
        uri.toString().toJS,
        web.RequestInit(method: 'GET', headers: requestHeaders),
      )
      .toDart;
  return GitHubAuthProbeResponse(
    statusCode: response.status,
    body: (await response.text().toDart).toDart,
  );
}
