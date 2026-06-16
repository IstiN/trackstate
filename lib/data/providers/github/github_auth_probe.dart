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
