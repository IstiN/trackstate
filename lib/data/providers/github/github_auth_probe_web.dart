@JS()
library;

import 'dart:js_interop';

import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

class GitHubAuthProbeResponse {
  const GitHubAuthProbeResponse({
    required this.statusCode,
    required this.body,
    this.headers = const <String, String>{},
  });

  final int statusCode;
  final String body;
  final Map<String, String> headers;
}

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
