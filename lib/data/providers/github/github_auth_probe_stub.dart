import 'dart:convert';

import 'package:http/http.dart' as http;

Future<Object?> fetchGitHubAuthProbeJson(
  Uri uri, {
  required Map<String, String> headers,
  http.Client? client,
}) async {
  final response = await (client ?? http.Client()).get(uri, headers: headers);
  return jsonDecode(response.body);
}
