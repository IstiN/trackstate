import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../domain/models/trackstate_models.dart';
import '../trackstate_provider.dart';

class GitHubTrackStateProvider implements TrackStateProviderAdapter {
  GitHubTrackStateProvider({
    http.Client? client,
    this.repositoryName = defaultRepositoryName,
    this.sourceRef = defaultSourceRef,
    this.dataRef = defaultDataRef,
  }) : _client = client;

  static const defaultRepositoryName = String.fromEnvironment(
    'TRACKSTATE_REPOSITORY',
    defaultValue: 'trackstate/trackstate',
  );
  static const defaultSourceRef = String.fromEnvironment(
    'TRACKSTATE_SOURCE_REF',
    defaultValue: 'main',
  );
  static const defaultDataRef = String.fromEnvironment(
    'TRACKSTATE_DATA_REF',
    defaultValue: 'main',
  );

  final http.Client? _client;
  final String repositoryName;
  final String sourceRef;

  RepositoryConnection? _connection;

  http.Client get _http => _client ?? http.Client();

  @override
  String get repositoryLabel => repositoryName;

  @override
  final String dataRef;

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async {
    final repoResponse = await _http.get(
      _githubUri('/repos/${connection.repository}'),
      headers: _githubHeaders(connection.token),
    );
    if (repoResponse.statusCode != 200) {
      throw TrackStateProviderException(
        'GitHub connection failed (${repoResponse.statusCode}): ${repoResponse.body}',
      );
    }
    final userJson =
        await _getGitHubJson('/user', token: connection.token)
            as Map<String, Object?>;
    _connection = connection;
    return RepositoryUser(
      login: userJson['login']?.toString() ?? 'github',
      displayName: userJson['name']?.toString() ?? '',
    );
  }

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async {
    final json =
        await _getGitHubJson(
              '/repos/$repositoryName/git/trees/$ref',
              queryParameters: {'recursive': '1'},
            )
            as Map<String, Object?>;
    final tree = json['tree'];
    if (tree is! List) {
      throw const TrackStateProviderException(
        'GitHub tree response did not contain a file list.',
      );
    }
    return tree
        .whereType<Map<String, Object?>>()
        .map(
          (entry) => RepositoryTreeEntry(
            path: entry['path']?.toString() ?? '',
            type: entry['type']?.toString() ?? '',
          ),
        )
        .toList();
  }

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async {
    final json =
        await _getGitHubJson(
              '/repos/$repositoryName/contents/$path',
              queryParameters: {'ref': ref},
            )
            as Map<String, Object?>;
    final encoded = json['content']?.toString().replaceAll('\n', '');
    if (encoded == null || encoded.isEmpty) {
      throw TrackStateProviderException(
        'GitHub content response for $path did not contain file content.',
      );
    }
    return RepositoryTextFile(
      path: path,
      content: utf8.decode(base64Decode(encoded)),
      revision: json['sha']?.toString(),
    );
  }

  @override
  Future<String> resolveWriteBranch() async =>
      _connection?.branch.isNotEmpty == true ? _connection!.branch : sourceRef;

  @override
  Future<RepositoryBranch> getBranch(String name) async {
    final response = await _http.get(
      _githubUri('/repos/$repositoryName/branches/$name'),
      headers: _githubHeaders(_connection?.token),
    );
    if (response.statusCode == 404) {
      return RepositoryBranch(name: name, exists: false, isCurrent: false);
    }
    if (response.statusCode != 200) {
      throw TrackStateProviderException(
        'GitHub branch lookup failed for $name (${response.statusCode}): ${response.body}',
      );
    }
    final currentBranch = await resolveWriteBranch();
    return RepositoryBranch(
      name: name,
      exists: true,
      isCurrent: currentBranch == name,
    );
  }

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async {
    final connection = _requireConnection();
    final response = await _http.put(
      _githubUri('/repos/${connection.repository}/contents/${request.path}'),
      headers: {
        ..._githubHeaders(connection.token),
        'content-type': 'application/json; charset=utf-8',
      },
      body: jsonEncode({
        'message': request.message,
        'content': base64Encode(utf8.encode(request.content)),
        'sha': request.expectedRevision,
        'branch': request.branch,
      }),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw TrackStateProviderException(
        'Could not save ${request.path} (${response.statusCode}): ${response.body}',
      );
    }
    final json = jsonDecode(response.body) as Map<String, Object?>;
    final content = json['content'];
    final revision = content is Map<String, Object?>
        ? content['sha']?.toString()
        : request.expectedRevision;
    return RepositoryWriteResult(
      path: request.path,
      branch: request.branch,
      revision: revision,
    );
  }

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async {
    final result = await writeTextFile(
      RepositoryWriteRequest(
        path: request.path,
        content: request.content,
        message: request.message,
        branch: request.branch,
        expectedRevision: request.expectedRevision,
      ),
    );
    return RepositoryCommitResult(
      branch: result.branch,
      message: request.message,
      revision: result.revision,
    );
  }

  @override
  Future<RepositoryPermission> getPermission() async {
    final connection = _connection;
    if (connection == null) {
      return const RepositoryPermission(
        canRead: true,
        canWrite: false,
        isAdmin: false,
      );
    }
    final repoJson =
        await _getGitHubJson('/repos/${connection.repository}')
            as Map<String, Object?>;
    return _permissionFromRepoJson(repoJson);
  }

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async {
    final json =
        await _getGitHubJson(
              '/repos/$repositoryName/contents/$path',
              queryParameters: {'ref': ref},
            )
            as Map<String, Object?>;
    final encoded = json['content']?.toString().replaceAll('\n', '');
    if (encoded == null || encoded.isEmpty) {
      throw TrackStateProviderException(
        'GitHub content response for $path did not contain file content.',
      );
    }
    return RepositoryAttachment(
      path: path,
      bytes: Uint8List.fromList(base64Decode(encoded)),
      revision: json['sha']?.toString(),
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    final connection = _requireConnection();
    final response = await _http.put(
      _githubUri('/repos/${connection.repository}/contents/${request.path}'),
      headers: {
        ..._githubHeaders(connection.token),
        'content-type': 'application/json; charset=utf-8',
      },
      body: jsonEncode({
        'message': request.message,
        'content': base64Encode(request.bytes),
        'sha': request.expectedRevision,
        'branch': request.branch,
      }),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      throw TrackStateProviderException(
        'Could not save attachment ${request.path} (${response.statusCode}): ${response.body}',
      );
    }
    final json = jsonDecode(response.body) as Map<String, Object?>;
    final content = json['content'];
    final revision = content is Map<String, Object?>
        ? content['sha']?.toString()
        : request.expectedRevision;
    return RepositoryAttachmentWriteResult(
      path: request.path,
      branch: request.branch,
      revision: revision,
    );
  }

  @override
  Future<bool> isLfsTracked(String path) async {
    try {
      final attributes = await readTextFile('.gitattributes', ref: dataRef);
      return _isLfsTrackedByAttributes(attributes.content, path);
    } on TrackStateProviderException {
      return false;
    }
  }

  Future<Object?> _getGitHubJson(
    String path, {
    Map<String, String>? queryParameters,
    String? token,
  }) async {
    final response = await _http.get(
      _githubUri(path, queryParameters),
      headers: _githubHeaders(token ?? _connection?.token),
    );
    if (response.statusCode != 200) {
      throw TrackStateProviderException(
        'GitHub API request failed for $path (${response.statusCode}): ${response.body}',
      );
    }
    return jsonDecode(response.body);
  }

  RepositoryConnection _requireConnection() {
    final connection = _connection;
    if (connection != null) return connection;
    throw const TrackStateProviderException(
      'Connect a GitHub token with repository Contents write access first.',
    );
  }
}

RepositoryPermission _permissionFromRepoJson(Map<String, Object?> json) {
  final permissions = json['permissions'];
  if (permissions is! Map) {
    return const RepositoryPermission(
      canRead: true,
      canWrite: false,
      isAdmin: false,
    );
  }
  final canRead = permissions['pull'] == true || permissions['push'] == true;
  final canWrite = permissions['push'] == true || permissions['admin'] == true;
  return RepositoryPermission(
    canRead: canRead,
    canWrite: canWrite,
    isAdmin: permissions['admin'] == true,
  );
}

Map<String, String> _githubHeaders(String? token) => {
  'accept': 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
  if (token != null && token.isNotEmpty) 'authorization': 'Bearer $token',
};

Uri _githubUri(String path, [Map<String, String>? queryParameters]) =>
    Uri.https('api.github.com', path, queryParameters);

bool _isLfsTrackedByAttributes(String attributes, String path) {
  final normalizedPath = path
      .replaceAll('\\', '/')
      .replaceFirst(RegExp(r'^/+'), '');
  var isTracked = false;
  for (final rawLine in LineSplitter.split(attributes)) {
    final line = rawLine.trim();
    if (line.isEmpty || line.startsWith('#')) {
      continue;
    }
    final parts = line.split(RegExp(r'\s+'));
    if (parts.length < 2 ||
        !_attributePatternMatches(parts.first, normalizedPath)) {
      continue;
    }
    for (final attribute in parts.skip(1)) {
      if (attribute == 'filter=lfs') {
        isTracked = true;
      } else if (attribute == '-filter' ||
          attribute == '!filter' ||
          attribute == 'filter') {
        isTracked = false;
      }
    }
  }
  return isTracked;
}

bool _attributePatternMatches(String pattern, String path) {
  final normalizedPattern = pattern.replaceAll('\\', '/');
  final anchored = normalizedPattern.startsWith('/');
  final candidate = anchored
      ? normalizedPattern.substring(1)
      : normalizedPattern;
  final hasDirectorySeparator = candidate.contains('/');
  final expression = StringBuffer('^');
  if (!anchored && !hasDirectorySeparator) {
    expression.write(r'(?:.*/)?');
  }
  for (var index = 0; index < candidate.length; index++) {
    final character = candidate[index];
    if (character == '*') {
      final isDoubleStar =
          index + 1 < candidate.length && candidate[index + 1] == '*';
      if (isDoubleStar) {
        expression.write('.*');
        index++;
      } else {
        expression.write(r'[^/]*');
      }
      continue;
    }
    if (character == '?') {
      expression.write(r'[^/]');
      continue;
    }
    expression.write(RegExp.escape(character));
  }
  expression.write(r'$');
  return RegExp(expression.toString()).hasMatch(path);
}
