import 'dart:async';
import 'dart:convert';
import 'dart:io';

const _deleteStatusEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_STATUS';
const _deleteBodyEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_BODY';
const _uploadStatusEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_UPLOAD_STATUS';
const _uploadBodyEnv = 'TRACKSTATE_CLI_FAIL_RELEASE_ASSET_UPLOAD_BODY';
const _releaseLookupStatusEnv =
    'TRACKSTATE_CLI_OVERRIDE_RELEASE_TAG_LOOKUP_STATUS';
const _releaseLookupBodyEnv = 'TRACKSTATE_CLI_OVERRIDE_RELEASE_TAG_LOOKUP_BODY';
const _releaseLookupPathEnv = 'TRACKSTATE_CLI_OVERRIDE_RELEASE_TAG_LOOKUP_PATH';
const _overridePrefix = '/_trackstate_override/rule';
final RegExp _releaseAssetDeletePath = RegExp(r'^/repos/[^/]+/[^/]+/releases/assets/\d+$');
final RegExp _releaseAssetUploadPath = RegExp(
  r'^/repos/[^/]+/[^/]+/releases/\d+/assets$',
);

Future<T> runWithOptionalGitHubHttpOverrides<T>(
  Future<T> Function() action,
) async {
  final rules = _configuredRules();
  if (rules.isEmpty) {
    return action();
  }

  final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
  unawaited(
    server.forEach((request) async {
      final rule = _ruleForRequest(request, rules);
      final statusCode = rule?.statusCode ?? 502;
      final body =
          rule?.body ??
          jsonEncode({
            'message': 'No TrackState CLI override matched ${request.method} '
                '${request.uri.path}.',
            'status': '$statusCode',
          });
      final bytes = utf8.encode(body);
      request.response.statusCode = statusCode;
      request.response.reasonPhrase = _defaultReasonPhrase(statusCode);
      request.response.headers.contentType = ContentType.json;
      request.response.headers.contentLength = bytes.length;
      request.response.add(bytes);
      await request.response.close();
    }),
  );

  final targetBaseUri = Uri(
    scheme: 'http',
    host: InternetAddress.loopbackIPv4.address,
    port: server.port,
  );
  final overrides = _GitHubHttpOverrides(
    targetBaseUri: targetBaseUri,
    rules: rules,
  );

  try {
    return await HttpOverrides.runZoned(
      action,
      createHttpClient: overrides.createHttpClient,
    );
  } finally {
    await server.close(force: true);
  }
}

List<_ResponseRule> _configuredRules() {
  final rules = <_ResponseRule>[];
  final deleteRule = _statusOverrideRule(
    method: 'DELETE',
    host: 'api.github.com',
    pathPattern: _releaseAssetDeletePath,
    statusEnv: _deleteStatusEnv,
    bodyEnv: _deleteBodyEnv,
    documentationUrl:
        'https://docs.github.com/rest/releases/assets#delete-a-release-asset',
  );
  if (deleteRule != null) {
    rules.add(deleteRule);
  }

  final uploadRule = _statusOverrideRule(
    method: 'POST',
    host: 'uploads.github.com',
    pathPattern: _releaseAssetUploadPath,
    statusEnv: _uploadStatusEnv,
    bodyEnv: _uploadBodyEnv,
    defaultMessage: 'Validation Failed',
    documentationUrl:
        'https://docs.github.com/rest/releases/assets#upload-a-release-asset',
  );
  if (uploadRule != null) {
    rules.add(uploadRule);
  }

  final releaseLookupPath = Platform.environment[_releaseLookupPathEnv]?.trim() ?? '';
  final releaseLookupBody = Platform.environment[_releaseLookupBodyEnv]?.trim() ?? '';
  final releaseLookupStatusText =
      Platform.environment[_releaseLookupStatusEnv]?.trim() ?? '';
  if (releaseLookupPath.isNotEmpty ||
      releaseLookupBody.isNotEmpty ||
      releaseLookupStatusText.isNotEmpty) {
    if (releaseLookupPath.isEmpty) {
      throw StateError(
        '$_releaseLookupPathEnv must be set when overriding release tag lookup.',
      );
    }
    final statusCode = releaseLookupStatusText.isEmpty
        ? 200
        : _parseStatusCode(
            releaseLookupStatusText,
            environmentVariable: _releaseLookupStatusEnv,
          );
    rules.add(
      _ResponseRule(
        method: 'GET',
        host: 'api.github.com',
        exactPath: releaseLookupPath,
        statusCode: statusCode,
        body: releaseLookupBody.isNotEmpty
            ? releaseLookupBody
            : jsonEncode({'message': 'OK'}),
      ),
    );
  }

  return rules;
}

_ResponseRule? _statusOverrideRule({
  required String method,
  required String host,
  required RegExp pathPattern,
  required String statusEnv,
  required String bodyEnv,
  required String documentationUrl,
  String? defaultMessage,
}) {
  final statusText = Platform.environment[statusEnv]?.trim() ?? '';
  if (statusText.isEmpty) {
    return null;
  }
  final statusCode = _parseStatusCode(statusText, environmentVariable: statusEnv);
  final body =
      Platform.environment[bodyEnv]?.trim().isNotEmpty == true
          ? Platform.environment[bodyEnv]!.trim()
          : jsonEncode({
              'message': defaultMessage ?? _defaultReasonPhrase(statusCode),
              'documentation_url': documentationUrl,
              'status': '$statusCode',
            });
  return _ResponseRule(
    method: method,
    host: host,
    pathPattern: pathPattern,
    statusCode: statusCode,
    body: body,
  );
}

int _parseStatusCode(String value, {required String environmentVariable}) {
  final statusCode = int.tryParse(value);
  if (statusCode == null || statusCode < 100 || statusCode > 599) {
    throw StateError(
      '$environmentVariable must be a valid HTTP status code when set.',
    );
  }
  return statusCode;
}

_ResponseRule? _ruleForRequest(HttpRequest request, List<_ResponseRule> rules) {
  final segments = request.uri.pathSegments;
  if (segments.length < 3 ||
      request.uri.path.startsWith(_overridePrefix) == false ||
      segments[0] != _overridePrefix.substring(1).split('/').first ||
      segments[1] != 'rule') {
    return null;
  }
  final index = int.tryParse(segments[2]);
  if (index == null || index < 0 || index >= rules.length) {
    return null;
  }
  return rules[index];
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

class _ResponseRule {
  _ResponseRule({
    required this.method,
    required this.host,
    this.pathPattern,
    this.exactPath,
    required this.statusCode,
    required this.body,
  });

  final String method;
  final String host;
  final RegExp? pathPattern;
  final String? exactPath;
  final int statusCode;
  final String body;

  bool matches(String requestMethod, Uri url) {
    if (requestMethod.toUpperCase() != method) {
      return false;
    }
    if (url.scheme != 'https' || url.host != host) {
      return false;
    }
    if (exactPath != null) {
      return url.path == exactPath;
    }
    return pathPattern?.hasMatch(url.path) ?? false;
  }
}

class _GitHubHttpOverrides extends HttpOverrides {
  _GitHubHttpOverrides({required this.targetBaseUri, required this.rules});

  final Uri targetBaseUri;
  final List<_ResponseRule> rules;

  @override
  HttpClient createHttpClient(SecurityContext? context) {
    final delegate = super.createHttpClient(context);
    return _InterceptingHttpClient(
      delegate,
      targetBaseUri: targetBaseUri,
      rules: rules,
    );
  }
}

class _InterceptingHttpClient implements HttpClient {
  _InterceptingHttpClient(
    this._delegate, {
    required this.targetBaseUri,
    required this.rules,
  });

  final HttpClient _delegate;
  final Uri targetBaseUri;
  final List<_ResponseRule> rules;

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
    for (var index = 0; index < rules.length; index += 1) {
      if (rules[index].matches(method.toUpperCase(), url)) {
        return targetBaseUri.replace(
          path: '$_overridePrefix/$index${url.path}',
          query: url.hasQuery ? url.query : null,
        );
      }
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
