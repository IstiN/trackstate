library http;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

class BaseRequest {
  BaseRequest(this.method, this.url);

  final String method;
  final Uri url;
  final Map<String, String> headers = <String, String>{};
}

class Request extends BaseRequest {
  Request(super.method, super.url);

  Uint8List bodyBytes = Uint8List(0);

  set body(String value) {
    bodyBytes = Uint8List.fromList(utf8.encode(value));
  }
}

class StreamedResponse {
  StreamedResponse(
    this.stream,
    this.statusCode, {
    Map<String, String>? headers,
  }) : headers = headers ?? const <String, String>{};

  final Stream<List<int>> stream;
  final int statusCode;
  final Map<String, String> headers;
}

class Response {
  Response(
    this.body,
    this.statusCode, {
    Map<String, String>? headers,
  }) : headers = headers ?? const <String, String>{},
       bodyBytes = Uint8List.fromList(utf8.encode(body));

  Response.bytes(
    List<int> bytes,
    this.statusCode, {
    Map<String, String>? headers,
  }) : bodyBytes = Uint8List.fromList(bytes),
       body = utf8.decode(bytes, allowMalformed: true),
       headers = headers ?? const <String, String>{};

  final String body;
  final int statusCode;
  final Map<String, String> headers;
  final Uint8List bodyBytes;

  static Future<Response> fromStream(StreamedResponse response) async {
    final bytes = <int>[];
    await for (final chunk in response.stream) {
      bytes.addAll(chunk);
    }
    return Response.bytes(bytes, response.statusCode, headers: response.headers);
  }
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

  Future<Response> post(
    Object? url, {
    Map<String, String>? headers,
    Object? body,
  }) async => Response('', 500);

  Future<Response> delete(
    Object? url, {
    Map<String, String>? headers,
    Object? body,
  }) async => Response('', 500);

  Future<StreamedResponse> send(BaseRequest request) async =>
      StreamedResponse(Stream<List<int>>.value(const <int>[]), 500);
}
