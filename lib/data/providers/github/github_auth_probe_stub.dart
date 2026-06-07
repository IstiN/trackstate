import 'package:http/http.dart' as http;

export 'github_auth_probe.dart';
import 'github_auth_probe.dart';

Future<GitHubAuthProbeResponse> fetchGitHubAuthProbeResponse(
  Uri uri, {
  required Map<String, String> headers,
  http.Client? client,
}) async {
  final response = await (client ?? http.Client()).get(uri, headers: headers);
  return GitHubAuthProbeResponse(
    statusCode: response.statusCode,
    body: response.body,
    headers: Map<String, String>.from(response.headers),
  );
}
