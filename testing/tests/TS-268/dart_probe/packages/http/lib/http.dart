library http;

class Response {
  Response(this.body, this.statusCode);

  final String body;
  final int statusCode;
}

class Client {
  Future<Response> get(
    Object? url, {
    Map<String, String>? headers,
  }) async => Response('', 500);

  Future<Response> put(
    Object? url, {
    Map<String, String>? headers,
    Object? body,
  }) async => Response('', 500);
}
