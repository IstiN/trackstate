import 'dart:typed_data';

class Response {
  Response(this.body, this.statusCode, {this.headers = const {}});

  final String body;
  final int statusCode;
  final Map<String, String> headers;

  Uint8List get bodyBytes => Uint8List.fromList(body.codeUnits);

  static Future<Response> fromStream(StreamedResponse response) async =>
      Response(response.body, response.statusCode, headers: response.headers);
}

class Request {
  Request(this.method, this.url, {this.headers = const {}, Object? body})
      : _body = body;

  final String method;
  final Uri url;
  final Map<String, String> headers;
  Object? _body;

  Object? get body => _body;
  set body(Object? value) => _body = value;

  set bodyBytes(List<int> value) => _body = String.fromCharCodes(value);
}

class StreamedResponse {
  const StreamedResponse(this.body, this.statusCode, {this.headers = const {}});

  final String body;
  final int statusCode;
  final Map<String, String> headers;
}

class Client {
  Future<Response> get(
    Uri url, {
    Map<String, String>? headers,
  }) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-38 Dart probe.');
  }

  Future<Response> put(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-38 Dart probe.');
  }

  Future<Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-38 Dart probe.');
  }

  Future<Response> patch(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-38 Dart probe.');
  }

  Future<Response> delete(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
  }) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-38 Dart probe.');
  }

  Future<StreamedResponse> send(Request request) async {
    throw UnsupportedError('HTTP calls are not supported in the TS-38 Dart probe.');
  }
}
