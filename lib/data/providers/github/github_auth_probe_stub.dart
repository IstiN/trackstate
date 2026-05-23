import 'package:http/http.dart' as http;

class GitHubAuthProbeResponse {
  const GitHubAuthProbeResponse({required this.statusCode, required this.body});

  final int statusCode;
  final String body;
}

Future<GitHubAuthProbeResponse> fetchGitHubAuthProbeResponse(
  Uri uri, {
  required Map<String, String> headers,
  http.Client? client,
}) async {
  final response = await (client ?? http.Client()).get(uri, headers: headers);
  return GitHubAuthProbeResponse(
    statusCode: response.statusCode,
    body: response.body,
  );
}
