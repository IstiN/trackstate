import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/legacy_hosted_workspace_migration_driver.dart';
import '../../core/models/legacy_hosted_workspace_migration_observation.dart';

class LegacyHostedWorkspaceMigrationWidgetDriver
    implements LegacyHostedWorkspaceMigrationDriver {
  LegacyHostedWorkspaceMigrationWidgetDriver(this._tester);

  static const _workspaceStateKey = 'trackstate.workspaceProfiles.state';
  static const _workspaceTokenPrefix = 'trackstate.githubToken.workspace.';

  final WidgetTester _tester;

  @override
  Future<LegacyHostedWorkspaceMigrationObservation> runScenario({
    required String activeRepository,
    required String defaultBranch,
    required String activeLegacyToken,
    required String unrelatedRepository,
    required String unrelatedLegacyToken,
    required String expectedDisplayName,
    required String expectedLogin,
    required String expectedInitials,
  }) async {
    final activeLegacyTokenKey =
        'trackstate.githubToken.${activeRepository.replaceAll('/', '.')}';
    final unrelatedLegacyTokenKey =
        'trackstate.githubToken.${unrelatedRepository.replaceAll('/', '.')}';
    final expectedWorkspaceId = 'hosted:$activeRepository@$defaultBranch';
    final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
      now: () => DateTime.utc(2026, 5, 13, 22, 0, 40),
    );
    const authStore = SharedPreferencesTrackStateAuthStore();

    SharedPreferences.setMockInitialValues(<String, Object>{
      activeLegacyTokenKey: activeLegacyToken,
      unrelatedLegacyTokenKey: unrelatedLegacyToken,
    });
    _tester.view.physicalSize = const Size(1440, 960);
    _tester.view.devicePixelRatio = 1;

    try {
      final overrides = _GitHubApiHttpOverrides(
        client: _FixtureHttpClient(_fixtureResponseFor),
      );
      return await HttpOverrides.runZoned(() async {
        await _tester.pumpWidget(
          TrackStateApp(
            key: UniqueKey(),
            workspaceProfileService: workspaceProfileService,
          ),
        );
        await _pumpUntilWorkspaceMigrated(
          service: workspaceProfileService,
          expectedWorkspaceId: expectedWorkspaceId,
        );

        final preferences = await SharedPreferences.getInstance();
        final workspaceState = await workspaceProfileService.loadState();
        final rawWorkspaceState = preferences.getString(_workspaceStateKey);
        final decodedWorkspaceState = rawWorkspaceState == null
            ? const <String, Object?>{}
            : (jsonDecode(rawWorkspaceState) as Map).cast<String, Object?>();
        final workspaceScopedKeys = preferences.getKeys().where((key) {
          return key.startsWith(_workspaceTokenPrefix);
        }).toList()..sort();

        return LegacyHostedWorkspaceMigrationObservation(
          workspaceState: workspaceState,
          storedProfileCount:
              (decodedWorkspaceState['profiles'] as List<Object?>?)?.length ??
              0,
          storedActiveWorkspaceId: decodedWorkspaceState['activeWorkspaceId']
              ?.toString(),
          storedMigrationComplete:
              decodedWorkspaceState['migrationComplete'] == true,
          rawWorkspaceState: rawWorkspaceState,
          workspaceScopedKeys: workspaceScopedKeys,
          workspaceToken: await authStore.readToken(
            workspaceId: expectedWorkspaceId,
          ),
          leftoverActiveLegacyRepositoryToken: await authStore.readToken(
            repository: activeRepository,
          ),
          unrelatedLegacyRepositoryToken: await authStore.readToken(
            repository: unrelatedRepository,
          ),
          connectedVisible: _isConnectedVisible(),
          displayNameVisible: find
              .text(expectedDisplayName)
              .evaluate()
              .isNotEmpty,
          loginVisible: _visibleTexts().any(
            (value) => value.contains(expectedLogin),
          ),
          initialsVisible: find.text(expectedInitials).evaluate().isNotEmpty,
          visibleTexts: _visibleTexts(),
        );
      }, createHttpClient: overrides.createHttpClient);
    } finally {
      _tester.view.resetPhysicalSize();
      _tester.view.resetDevicePixelRatio();
    }
  }

  Future<void> _pumpUntilWorkspaceMigrated({
    required WorkspaceProfileService service,
    required String expectedWorkspaceId,
  }) async {
    const step = Duration(milliseconds: 100);
    for (var attempt = 0; attempt < 80; attempt++) {
      await _tester.pump(step);
      final state = await service.loadState();
      if (state.activeWorkspaceId == expectedWorkspaceId) {
        await _pumpFrames(6);
        return;
      }
    }
  }

  Future<void> _pumpFrames(int count) async {
    for (var index = 0; index < count; index++) {
      await _tester.pump(const Duration(milliseconds: 100));
    }
  }

  bool _isConnectedVisible() {
    return find.text('Connected').evaluate().isNotEmpty ||
        find.bySemanticsLabel(RegExp(r'^Connected$')).evaluate().isNotEmpty ||
        find.text('Attachments limited').evaluate().isNotEmpty ||
        find
            .bySemanticsLabel(RegExp(r'^Attachments limited$'))
            .evaluate()
            .isNotEmpty ||
        _visibleTexts().any((value) => value.contains('Connected as '));
  }

  List<String> _visibleTexts() {
    final snapshot = <String>[];
    for (final widget in _tester.widgetList<Text>(find.byType(Text))) {
      final value = widget.data?.trim();
      if (value == null || value.isEmpty || snapshot.contains(value)) {
        continue;
      }
      snapshot.add(value);
    }
    return snapshot;
  }
}

class _GitHubApiHttpOverrides extends HttpOverrides {
  _GitHubApiHttpOverrides({required this.client});

  final HttpClient client;

  @override
  HttpClient createHttpClient(SecurityContext? context) => client;
}

class _FixtureHttpClient implements HttpClient {
  _FixtureHttpClient(this._responder);

  final _FixtureHttpResponseData Function(String method, Uri url) _responder;

  @override
  Future<HttpClientRequest> openUrl(String method, Uri url) async {
    return _FixtureHttpClientRequest(
      method: method,
      url: url,
      responder: _responder,
    );
  }

  @override
  Future<HttpClientRequest> getUrl(Uri url) => openUrl('GET', url);

  @override
  Future<HttpClientRequest> open(
    String method,
    String host,
    int port,
    String path,
  ) => openUrl(method, _composeUri(host: host, port: port, path: path));

  @override
  Future<HttpClientRequest> get(String host, int port, String path) {
    return getUrl(_composeUri(host: host, port: port, path: path));
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
  void close({bool force = false}) {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FixtureHttpClientRequest implements HttpClientRequest {
  _FixtureHttpClientRequest({
    required this.method,
    required this.url,
    required this.responder,
  });

  @override
  final String method;
  @override
  final Uri url;
  @override
  final _FixtureHttpHeaders headers = _FixtureHttpHeaders();

  final _FixtureHttpResponseData Function(String method, Uri url) responder;
  final BytesBuilder _body = BytesBuilder();

  @override
  Encoding encoding = utf8;
  @override
  bool followRedirects = true;
  @override
  int maxRedirects = 5;
  @override
  bool persistentConnection = true;
  @override
  int contentLength = -1;
  @override
  bool bufferOutput = false;

  @override
  void add(List<int> data) {
    _body.add(data);
  }

  @override
  Future<void> addStream(Stream<List<int>> stream) async {
    await for (final chunk in stream) {
      _body.add(chunk);
    }
  }

  @override
  Future<HttpClientResponse> close() async {
    return _FixtureHttpClientResponse(responder(method, url));
  }

  @override
  Future<void> flush() async {}

  @override
  void write(Object? object) {
    add(encoding.encode('$object'));
  }

  @override
  void writeAll(Iterable<dynamic> objects, [String separator = '']) {
    write(objects.join(separator));
  }

  @override
  void writeCharCode(int charCode) {
    add(<int>[charCode]);
  }

  @override
  void writeln([Object? object = '']) {
    write(object);
    write('\n');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FixtureHttpClientResponse extends Stream<List<int>>
    implements HttpClientResponse {
  _FixtureHttpClientResponse(this._response);

  final _FixtureHttpResponseData _response;

  @override
  int get statusCode => _response.statusCode;

  @override
  int get contentLength => _response.body.length;

  @override
  HttpHeaders get headers => _response.headers;

  @override
  String get reasonPhrase => _response.reasonPhrase;

  @override
  bool get persistentConnection => false;

  @override
  bool get isRedirect => false;

  @override
  List<RedirectInfo> get redirects => const <RedirectInfo>[];

  @override
  HttpClientResponseCompressionState get compressionState =>
      HttpClientResponseCompressionState.notCompressed;

  @override
  StreamSubscription<List<int>> listen(
    void Function(List<int> event)? onData, {
    Function? onError,
    void Function()? onDone,
    bool? cancelOnError,
  }) {
    return Stream<List<int>>.fromIterable(<List<int>>[_response.body]).listen(
      onData,
      onError: onError,
      onDone: onDone,
      cancelOnError: cancelOnError,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FixtureHttpHeaders implements HttpHeaders {
  final Map<String, List<String>> _values = <String, List<String>>{};

  @override
  ContentType? contentType;

  @override
  int contentLength = -1;

  @override
  void add(String name, Object value, {bool preserveHeaderCase = false}) {
    final normalizedName = name.toLowerCase();
    final entry = _values.putIfAbsent(normalizedName, () => <String>[]);
    entry.add(value.toString());
    if (normalizedName == HttpHeaders.contentTypeHeader) {
      contentType = ContentType.parse(value.toString());
    }
    if (normalizedName == HttpHeaders.contentLengthHeader) {
      contentLength = int.tryParse(value.toString()) ?? contentLength;
    }
  }

  @override
  void set(String name, Object value, {bool preserveHeaderCase = false}) {
    _values[name.toLowerCase()] = <String>[value.toString()];
    if (name.toLowerCase() == HttpHeaders.contentTypeHeader) {
      contentType = ContentType.parse(value.toString());
    }
    if (name.toLowerCase() == HttpHeaders.contentLengthHeader) {
      contentLength = int.tryParse(value.toString()) ?? contentLength;
    }
  }

  @override
  List<String>? operator [](String name) => _values[name.toLowerCase()];

  @override
  String? value(String name) {
    final values = _values[name.toLowerCase()];
    if (values == null || values.isEmpty) {
      return null;
    }
    return values.single;
  }

  @override
  void forEach(void Function(String name, List<String> values) action) {
    _values.forEach((name, values) {
      action(name, List<String>.unmodifiable(values));
    });
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FixtureHttpResponseData {
  _FixtureHttpResponseData({
    required this.statusCode,
    required this.reasonPhrase,
    required List<int> body,
    ContentType? contentType,
  }) : body = List<int>.unmodifiable(body),
       headers = _FixtureHttpHeaders() {
    headers.contentType = contentType ?? ContentType.json;
    headers.contentLength = this.body.length;
    headers.set(HttpHeaders.contentTypeHeader, headers.contentType.toString());
    headers.set(HttpHeaders.contentLengthHeader, '${this.body.length}');
  }

  final int statusCode;
  final String reasonPhrase;
  final List<int> body;
  final _FixtureHttpHeaders headers;
}

_FixtureHttpResponseData _fixtureResponseFor(String method, Uri url) {
  final normalizedMethod = method.toUpperCase();
  final path = url.path;
  if (normalizedMethod != 'GET' || url.host != 'api.github.com') {
    return _jsonResponse(404, <String, Object?>{
      'message': 'Unhandled fixture request: $method $url',
    });
  }
  if (path == '/repos/trackstate/trackstate') {
    return _jsonResponse(200, _repositoryResponse);
  }
  if (path == '/user') {
    return _jsonResponse(200, _userResponse);
  }
  if (path == '/repos/trackstate/trackstate/branches/main') {
    return _jsonResponse(200, _branchResponse);
  }
  if (path == '/repos/trackstate/trackstate/git/trees/main') {
    return _jsonResponse(200, _treeResponse);
  }
  final content = _contentResponses[path];
  if (content != null) {
    return _jsonResponse(200, <String, Object?>{
      'content': base64Encode(utf8.encode(content)),
      'sha': 'fixture-sha',
    });
  }
  return _jsonResponse(404, <String, Object?>{
    'message': 'Missing fixture for $method $url',
  });
}

_FixtureHttpResponseData _jsonResponse(
  int statusCode,
  Map<String, Object?> body,
) {
  return _FixtureHttpResponseData(
    statusCode: statusCode,
    reasonPhrase: statusCode == 200 ? 'OK' : 'Not Found',
    body: utf8.encode(jsonEncode(body)),
  );
}

const _repositoryResponse = <String, Object?>{
  'full_name': 'trackstate/trackstate',
  'permissions': <String, Object?>{'pull': true, 'push': true, 'admin': false},
};

const _userResponse = <String, Object?>{
  'login': 'demo-user',
  'name': 'Demo User',
  'id': 665,
  'email': 'demo-user@example.com',
};

const _branchResponse = <String, Object?>{
  'name': 'main',
  'commit': <String, Object?>{'sha': 'fixture-sha'},
};

const _treeResponse = <String, Object?>{
  'tree': <Map<String, Object?>>[
    {'path': 'DEMO/.trackstate/index/issues.json', 'type': 'blob'},
    {'path': 'DEMO/project.json', 'type': 'blob'},
    {'path': 'DEMO/config/statuses.json', 'type': 'blob'},
    {'path': 'DEMO/config/issue-types.json', 'type': 'blob'},
    {'path': 'DEMO/config/fields.json', 'type': 'blob'},
    {'path': 'DEMO/DEMO-1/main.md', 'type': 'blob'},
    {'path': 'DEMO/DEMO-1/acceptance_criteria.md', 'type': 'blob'},
  ],
};

const _contentResponses = <String, String>{
  '/repos/trackstate/trackstate/contents/DEMO/.trackstate/index/issues.json':
      '[{"key":"DEMO-1","path":"DEMO/DEMO-1/main.md","children":[],"summary":"Hosted runtime sample issue","issueType":"Story","status":"In Progress","priority":"High","assignee":"demo-user","updated":"just now"}]',
  '/repos/trackstate/trackstate/contents/DEMO/project.json':
      '{"key":"DEMO","name":"Demo Project"}',
  '/repos/trackstate/trackstate/contents/DEMO/config/statuses.json':
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]',
  '/repos/trackstate/trackstate/contents/DEMO/config/issue-types.json':
      '[{"name":"Epic"},{"name":"Story"}]',
  '/repos/trackstate/trackstate/contents/DEMO/config/fields.json':
      '[{"name":"Summary"},{"name":"Priority"}]',
  '/repos/trackstate/trackstate/contents/DEMO/DEMO-1/main.md':
      '---\nkey: DEMO-1\nproject: DEMO\nissueType: Story\nstatus: In Progress\npriority: High\nsummary: Hosted runtime sample issue\nassignee: demo-user\nreporter: demo-admin\nlabels:\n  - hosted\ncomponents:\n  - web\nparent: null\nepic: null\nupdated: 2026-05-05T00:00:00Z\n---\n\n# Description\n\nLoaded through the hosted setup repository.\n',
  '/repos/trackstate/trackstate/contents/DEMO/DEMO-1/acceptance_criteria.md':
      '- Verify GitHub runtime startup.\n- Keep Local Git disabled by default.\n',
};
