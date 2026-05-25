library testing;

import 'dart:async';

import 'http.dart';

typedef MockClientHandler = Future<Response> Function(BaseRequest request);

class MockClient extends Client {
  MockClient(this._handler);

  final MockClientHandler _handler;

  @override
  Future<Response> get(
    Object? url, {
    Map<String, String>? headers,
  }) => _sendSimple('GET', url, headers: headers);

  @override
  Future<Response> put(
    Object? url, {
    Map<String, String>? headers,
    Object? body,
  }) => _sendSimple('PUT', url, headers: headers, body: body);

  @override
  Future<Response> post(
    Object? url, {
    Map<String, String>? headers,
    Object? body,
  }) => _sendSimple('POST', url, headers: headers, body: body);

  @override
  Future<Response> delete(
    Object? url, {
    Map<String, String>? headers,
    Object? body,
  }) => _sendSimple('DELETE', url, headers: headers, body: body);

  @override
  Future<StreamedResponse> send(BaseRequest request) async {
    final response = await _handler(request);
    return StreamedResponse(
      Stream<List<int>>.value(response.bodyBytes),
      response.statusCode,
      headers: response.headers,
    );
  }

  Future<Response> _sendSimple(
    String method,
    Object? url, {
    Map<String, String>? headers,
    Object? body,
  }) {
    final request = Request(method, Uri.parse(url.toString()));
    if (headers != null) {
      request.headers.addAll(headers);
    }
    if (body != null) {
      request.body = body.toString();
    }
    return _handler(request);
  }
}
