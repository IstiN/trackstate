import 'dart:async';
import 'dart:convert';
import 'dart:io';

const _deleteStatusEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_STATUS';
const _deleteBodyEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_BODY';
const _requestLogEnv = 'TRACKSTATE_CLI_REQUEST_LOG_FILE';
final RegExp _releaseAssetDeletePath = RegExp(
  r'^/repos/[^/]+/[^/]+/releases/assets/\d+$',
);
const Set<String> _githubRequestHosts = <String>{
  'api.github.com',
  'uploads.github.com',
};

Future<T> runWithCliHttpInstrumentation<T>(Future<T> Function() action) async {
  final deleteFailure = _DeleteFailureConfig.tryParse();
  final requestLogPath = Platform.environment[_requestLogEnv]?.trim() ?? '';
  final requestLogger = requestLogPath.isEmpty
      ? null
      : _CliHttpRequestLogger(requestLogPath);
  if (deleteFailure == null && requestLogger == null) {
    return action();
  }

  HttpServer? server;
  Uri? targetUri;
  if (deleteFailure != null) {
    server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final bodyBytes = utf8.encode(deleteFailure.body);
    unawaited(
      server.forEach((request) async {
        request.response.statusCode = deleteFailure.statusCode;
        request.response.reasonPhrase = _defaultReasonPhrase(
          deleteFailure.statusCode,
        );
        request.response.headers.contentType = ContentType.json;
        request.response.headers.contentLength = bodyBytes.length;
        request.response.add(bodyBytes);
        await request.response.close();
      }),
    );
    targetUri = Uri(
      scheme: 'http',
      host: InternetAddress.loopbackIPv4.address,
      port: server.port,
      path: '/',
    );
  }

  final overrides = _CliHarnessHttpOverrides(
    targetUri: targetUri,
    requestLogger: requestLogger,
  );
  try {
    return await HttpOverrides.runZoned(
      action,
      createHttpClient: overrides.createHttpClient,
    );
  } finally {
    await requestLogger?.flush();
    await server?.close(force: true);
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

class _DeleteFailureConfig {
  const _DeleteFailureConfig({required this.statusCode, required this.body});

  final int statusCode;
  final String body;

  static _DeleteFailureConfig? tryParse() {
    final statusText = Platform.environment[_deleteStatusEnv]?.trim() ?? '';
    if (statusText.isEmpty) {
      return null;
    }
    final statusCode = int.tryParse(statusText);
    if (statusCode == null || statusCode < 100 || statusCode > 599) {
      throw StateError(
        '$_deleteStatusEnv must be a valid HTTP status code when set.',
      );
    }
    final body = Platform.environment[_deleteBodyEnv]?.trim().isNotEmpty == true
        ? Platform.environment[_deleteBodyEnv]!.trim()
        : jsonEncode({
            'message': _defaultReasonPhrase(statusCode),
            'documentation_url':
                'https://docs.github.com/rest/releases/assets#delete-a-release-asset',
            'status': '$statusCode',
          });
    return _DeleteFailureConfig(statusCode: statusCode, body: body);
  }
}

class _CliHarnessHttpOverrides extends HttpOverrides {
  _CliHarnessHttpOverrides({
    required this.targetUri,
    required this.requestLogger,
  });

  final Uri? targetUri;
  final _CliHttpRequestLogger? requestLogger;

  @override
  HttpClient createHttpClient(SecurityContext? context) {
    final delegate = super.createHttpClient(context);
    return _CliHarnessInterceptingHttpClient(
      delegate,
      targetUri: targetUri,
      requestLogger: requestLogger,
    );
  }
}

class _CliHarnessInterceptingHttpClient implements HttpClient {
  _CliHarnessInterceptingHttpClient(
    this._delegate, {
    required this.targetUri,
    required this.requestLogger,
  });

  final HttpClient _delegate;
  final Uri? targetUri;
  final _CliHttpRequestLogger? requestLogger;

  @override
  Future<HttpClientRequest> openUrl(String method, Uri url) {
    return _delegate.openUrl(method, _rewriteAndRecord(method, url));
  }

  @override
  Future<HttpClientRequest> deleteUrl(Uri url) => openUrl('DELETE', url);

  @override
  Future<HttpClientRequest> getUrl(Uri url) => openUrl('GET', url);

  @override
  Future<HttpClientRequest> postUrl(Uri url) => openUrl('POST', url);

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
  Future<HttpClientRequest> get(String host, int port, String path) {
    return getUrl(_composeUri(host: host, port: port, path: path));
  }

  @override
  Future<HttpClientRequest> post(String host, int port, String path) {
    return postUrl(_composeUri(host: host, port: port, path: path));
  }

  @override
  void close({bool force = false}) {
    _delegate.close(force: force);
  }

  Uri _rewriteAndRecord(String method, Uri url) {
    final rewrittenUrl = _rewrite(method, url);
    requestLogger?.record(
      method: method,
      url: url,
      rewrittenUrl: rewrittenUrl == url ? null : rewrittenUrl,
    );
    return rewrittenUrl;
  }

  Uri _rewrite(String method, Uri url) {
    final normalizedMethod = method.toUpperCase();
    if (normalizedMethod == 'DELETE' &&
        targetUri != null &&
        url.scheme == 'https' &&
        url.host == 'api.github.com' &&
        _releaseAssetDeletePath.hasMatch(url.path)) {
      return targetUri!.replace(query: url.query);
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

class _CliHttpRequestLogger {
  _CliHttpRequestLogger(this.outputPath);

  final String outputPath;
  final List<Map<String, Object?>> _entries = <Map<String, Object?>>[];

  void record({
    required String method,
    required Uri url,
    required Uri? rewrittenUrl,
  }) {
    if (!_githubRequestHosts.contains(url.host)) {
      return;
    }
    _entries.add(<String, Object?>{
      'method': method.toUpperCase(),
      'url': url.toString(),
      'host': url.host,
      'path': url.path,
      'query': url.hasQuery ? url.query : null,
      'rewrittenUrl': rewrittenUrl?.toString(),
    });
  }

  Future<void> flush() async {
    final file = File(outputPath);
    await file.parent.create(recursive: true);
    await file.writeAsString(jsonEncode(_entries), flush: true);
  }
}
