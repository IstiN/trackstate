@JS()
library;

import 'dart:js_interop';

import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

export 'github_auth_probe.dart';
import 'github_auth_probe.dart';

Future<GitHubAuthProbeResponse> fetchGitHubAuthProbeResponse(
  Uri uri, {
  required Map<String, String> headers,
  Object? client,
}) async {
  if (client case final http.Client httpClient) {
    final response = await httpClient.get(uri, headers: headers);
    return GitHubAuthProbeResponse(
      statusCode: response.statusCode,
      body: response.body,
      headers: Map<String, String>.from(response.headers),
    );
  }
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
