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
    throw UnsupportedError('HTTP GET is not implemented by the TS-117 stub.');
  }

  Future<Response> put(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    throw UnsupportedError('HTTP PUT is not implemented by the TS-117 stub.');
  }
}
