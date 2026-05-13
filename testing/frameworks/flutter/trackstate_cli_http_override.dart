import 'dart:async';
import 'dart:convert';
import 'dart:io';

const _deleteStatusEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_STATUS';
const _deleteBodyEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_BODY';
final RegExp _releaseAssetDeletePath = RegExp(r'^/repos/[^/]+/[^/]+/releases/assets/\d+$');

Future<T> runWithOptionalReleaseAssetDeleteFailure<T>(
  Future<T> Function() action,
) async {
  final statusText = Platform.environment[_deleteStatusEnv]?.trim() ?? '';
  if (statusText.isEmpty) {
    return action();
  }

  final statusCode = int.tryParse(statusText);
  if (statusCode == null || statusCode < 100 || statusCode > 599) {
    throw StateError(
      '$_deleteStatusEnv must be a valid HTTP status code when set.',
    );
  }

  final body =
      Platform.environment[_deleteBodyEnv]?.trim().isNotEmpty == true
          ? Platform.environment[_deleteBodyEnv]!.trim()
          : jsonEncode({
              'message': _defaultReasonPhrase(statusCode),
              'documentation_url':
                  'https://docs.github.com/rest/releases/assets#delete-a-release-asset',
              'status': '$statusCode',
            });

  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  unawaited(
    server.forEach((request) async {
      final bytes = utf8.encode(body);
      request.response.statusCode = statusCode;
      request.response.reasonPhrase = _defaultReasonPhrase(statusCode);
      request.response.headers.contentType = ContentType.json;
      request.response.headers.contentLength = bytes.length;
      request.response.add(bytes);
      await request.response.close();
    }),
  );

  final targetUri = Uri(
    scheme: 'http',
    host: InternetAddress.loopbackIPv4.address,
    port: server.port,
    path: '/',
  );
  final overrides = _ReleaseAssetDeleteHttpOverrides(targetUri: targetUri);

  try {
    return await HttpOverrides.runZoned(
      action,
      createHttpClient: overrides.createHttpClient,
    );
  } finally {
    await server.close(force: true);
  }
}

String _defaultReasonPhrase(int statusCode) {
  return switch (statusCode) {
    400 => 'Bad Request',
    401 => 'Unauthorized',
    403 => 'Forbidden',
    404 => 'Not Found',
    409 => 'Conflict',
    422 => 'Unprocessable Entity',
    500 => 'Internal Server Error',
    502 => 'Bad Gateway',
    503 => 'Service Unavailable',
    504 => 'Gateway Timeout',
    _ => 'HTTP $statusCode',
  };
}

class _ReleaseAssetDeleteHttpOverrides extends HttpOverrides {
  _ReleaseAssetDeleteHttpOverrides({required this.targetUri});

  final Uri targetUri;

  @override
  HttpClient createHttpClient(SecurityContext? context) {
    final delegate = super.createHttpClient(context);
    return _ReleaseAssetDeleteInterceptingHttpClient(
      delegate,
      targetUri: targetUri,
    );
  }
}

class _ReleaseAssetDeleteInterceptingHttpClient implements HttpClient {
  _ReleaseAssetDeleteInterceptingHttpClient(
    this._delegate, {
    required this.targetUri,
  });

  final HttpClient _delegate;
  final Uri targetUri;

  @override
  Future<HttpClientRequest> openUrl(String method, Uri url) {
    return _delegate.openUrl(method, _rewrite(method, url));
  }

  @override
  Future<HttpClientRequest> deleteUrl(Uri url) {
    return _delegate.deleteUrl(_rewrite('DELETE', url));
  }

  @override
  Future<HttpClientRequest> open(
    String method,
    String host,
    int port,
    String path,
  ) {
    return openUrl(method, _composeUri(host: host, port: port, path: path));
  }

  @override
  Future<HttpClientRequest> delete(String host, int port, String path) {
    return deleteUrl(_composeUri(host: host, port: port, path: path));
  }

  @override
  void close({bool force = false}) {
    _delegate.close(force: force);
  }

  Uri _rewrite(String method, Uri url) {
    final normalizedMethod = method.toUpperCase();
    if (normalizedMethod == 'DELETE' &&
        url.scheme == 'https' &&
        url.host == 'api.github.com' &&
        _releaseAssetDeletePath.hasMatch(url.path)) {
      return targetUri.replace(queryParameters: url.queryParameters);
    }
    return url;
  }

  Uri _composeUri({
    required String host,
    required int port,
    required String path,
  }) {
    final suffix = port == 443 ? '' : ':$port';
    return Uri.parse('https://$host$suffix$path');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
