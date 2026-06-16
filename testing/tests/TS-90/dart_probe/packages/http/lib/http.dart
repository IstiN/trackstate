class Response {
  const Response(this.body, this.statusCode);

  final String body;
  final int statusCode;
}

class Client {
  Future<Response> get(
    Uri url, {
    Map<String, String>? headers,
  }) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-90 Dart probe.');
  }

  Future<Response> put(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-90 Dart probe.');
  }
}
