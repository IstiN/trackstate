import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../domain/models/trackstate_models.dart';
import '../trackstate_provider.dart';

class GitHubTrackStateProvider
    implements
        TrackStateProviderAdapter,
        RepositoryFileMutator,
        RepositoryHistoryReader {
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
  ProviderType get providerType => ProviderType.github;

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
  Future<RepositoryCommitResult> applyFileChanges(
    RepositoryFileChangeRequest request,
  ) async {
    final connection = _requireConnection();
    final headCommitSha = await _gitRefSha(
      repository: connection.repository,
      ref: 'heads/${request.branch}',
    );
    if (request.changes.isEmpty) {
      return RepositoryCommitResult(
        branch: request.branch,
        message: request.message,
        revision: headCommitSha,
      );
    }

    final baseTreeSha = await _commitTreeSha(
      repository: connection.repository,
      commitSha: headCommitSha,
    );
    for (final change in request.changes) {
      await _ensureExpectedRevisionMatches(
        repository: connection.repository,
        ref: headCommitSha,
        change: change,
      );
    }

    final treeEntries = <Map<String, Object?>>[];
    for (final change in request.changes) {
      switch (change) {
        case RepositoryTextFileChange():
          treeEntries.add({
            'path': change.path,
            'mode': '100644',
            'type': 'blob',
            'content': change.content,
          });
        case RepositoryBinaryFileChange():
          final blobSha = await _createBlob(
            repository: connection.repository,
            bytes: change.bytes,
          );
          treeEntries.add({
            'path': change.path,
            'mode': '100644',
            'type': 'blob',
            'sha': blobSha,
          });
        case RepositoryDeleteFileChange():
          treeEntries.add({
            'path': change.path,
            'mode': '100644',
            'type': 'blob',
            'sha': null,
          });
      }
    }

    final treeSha = await _createTree(
      repository: connection.repository,
      baseTreeSha: baseTreeSha,
      entries: treeEntries,
    );
    if (treeSha == baseTreeSha) {
      return RepositoryCommitResult(
        branch: request.branch,
        message: request.message,
        revision: headCommitSha,
      );
    }

    final commitSha = await _createGitCommit(
      repository: connection.repository,
      message: request.message,
      treeSha: treeSha,
      parentCommitSha: headCommitSha,
    );
    await _updateGitRef(
      repository: connection.repository,
      ref: 'heads/${request.branch}',
      commitSha: commitSha,
    );
    return RepositoryCommitResult(
      branch: request.branch,
      message: request.message,
      revision: commitSha,
    );
  }

  @override
  Future<void> ensureCleanWorktree() async {}

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
    final pointerText = utf8.decode(base64Decode(encoded));
    final pointerInfo = _parseLfsPointer(pointerText);
    var bytes = Uint8List.fromList(base64Decode(encoded));
    if (pointerInfo != null) {
      final downloadUrl = json['download_url']?.toString();
      if (downloadUrl != null && downloadUrl.isNotEmpty) {
        final response = await _http.get(
          Uri.parse(downloadUrl),
          headers: _githubHeaders(_connection?.token),
        );
        if (response.statusCode == 200) {
          bytes = response.bodyBytes;
        }
      }
    }
    return RepositoryAttachment(
      path: path,
      bytes: bytes,
      revision: json['sha']?.toString(),
      lfsOid: pointerInfo?.oid,
      declaredSizeBytes: pointerInfo?.sizeBytes,
    );
  }

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async {
    final connection = _requireConnection();
    if (await _isLfsTracked(request.path, ref: request.branch)) {
      throw TrackStateProviderException(
        'GitHub LFS attachment uploads are not yet implemented for '
        '${request.path}.',
      );
    }
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
  Future<bool> isLfsTracked(String path) => _isLfsTracked(path, ref: dataRef);

  @override
  Future<List<RepositoryHistoryCommit>> listHistory({
    required String ref,
    required String path,
    int limit = 50,
  }) async {
    final commitsJson =
        await _getGitHubJson(
              '/repos/$repositoryName/commits',
              queryParameters: {
                'sha': ref,
                'path': path,
                'per_page': '$limit',
              },
            )
            as List<Object?>;
    final commits = <RepositoryHistoryCommit>[];
    for (final entry in commitsJson.whereType<Map<String, Object?>>()) {
      final sha = entry['sha']?.toString();
      if (sha == null || sha.isEmpty) {
        continue;
      }
      final detail =
          await _getGitHubJson('/repos/$repositoryName/commits/$sha')
              as Map<String, Object?>;
      final commitJson = detail['commit'] as Map<String, Object?>? ?? const {};
      final authorJson = commitJson['author'] as Map<String, Object?>? ?? const {};
      final files = detail['files'] as List<Object?>? ?? const [];
      commits.add(
        RepositoryHistoryCommit(
          sha: sha,
          parentSha: (detail['parents'] as List<Object?>?)
              ?.whereType<Map<String, Object?>>()
              .firstOrNull?['sha']
              ?.toString(),
          author: authorJson['name']?.toString() ?? 'github',
          timestamp: authorJson['date']?.toString() ?? '',
          message: commitJson['message']?.toString() ?? '',
          changes: [
            for (final file in files.whereType<Map<String, Object?>>())
              RepositoryHistoryFileChange(
                path: file['filename']?.toString() ?? '',
                previousPath: file['previous_filename']?.toString(),
                changeType: switch (file['status']?.toString()) {
                  'added' => RepositoryHistoryChangeType.added,
                  'removed' => RepositoryHistoryChangeType.removed,
                  'renamed' => RepositoryHistoryChangeType.renamed,
                  _ => RepositoryHistoryChangeType.modified,
                },
              ),
          ],
        ),
      );
    }
    return commits;
  }

  Future<bool> _isLfsTracked(String path, {required String ref}) async {
    try {
      final attributes = await readTextFile('.gitattributes', ref: ref);
      return _isLfsTrackedByAttributes(attributes.content, path);
    } on TrackStateProviderException {
      return false;
    }
  }

  Future<void> _ensureExpectedRevisionMatches({
    required String repository,
    required String ref,
    required RepositoryFileChange change,
  }) async {
    final expectedRevision = change.expectedRevision;
    if (change is RepositoryDeleteFileChange && expectedRevision == null) {
      return;
    }
    final currentRevision = await _currentPathRevision(
      repository: repository,
      path: change.path,
      ref: ref,
    );
    if (expectedRevision == currentRevision) {
      return;
    }
    throw TrackStateProviderException(
      'Cannot save ${change.path} because it changed in the current branch. '
      'Expected revision ${expectedRevision ?? 'for a new file'}, '
      'found ${currentRevision ?? 'no file at HEAD'}.',
    );
  }

  Future<String?> _currentPathRevision({
    required String repository,
    required String path,
    required String ref,
  }) async {
    final response = await _http.get(
      _githubUri('/repos/$repository/contents/$path', {'ref': ref}),
      headers: _githubHeaders(_connection?.token),
    );
    if (response.statusCode == 404) {
      return null;
    }
    if (response.statusCode != 200) {
      throw TrackStateProviderException(
        'GitHub API request failed for /repos/$repository/contents/$path '
        '(${response.statusCode}): ${response.body}',
      );
    }
    final json = jsonDecode(response.body) as Map<String, Object?>;
    return json['sha']?.toString();
  }

  Future<String> _gitRefSha({
    required String repository,
    required String ref,
  }) async {
    final json =
        await _sendGitHubJson(
              method: 'GET',
              path: '/repos/$repository/git/ref/$ref',
            )
            as Map<String, Object?>;
    final object = json['object'];
    if (object is! Map<String, Object?> || object['sha'] == null) {
      throw TrackStateProviderException(
        'GitHub ref response for $ref did not contain a commit SHA.',
      );
    }
    return object['sha']!.toString();
  }

  Future<String> _commitTreeSha({
    required String repository,
    required String commitSha,
  }) async {
    final json =
        await _sendGitHubJson(
              method: 'GET',
              path: '/repos/$repository/git/commits/$commitSha',
            )
            as Map<String, Object?>;
    final tree = json['tree'];
    if (tree is! Map<String, Object?> || tree['sha'] == null) {
      throw TrackStateProviderException(
        'GitHub commit $commitSha did not expose its tree SHA.',
      );
    }
    return tree['sha']!.toString();
  }

  Future<String> _createBlob({
    required String repository,
    required Uint8List bytes,
  }) async {
    final json =
        await _sendGitHubJson(
              method: 'POST',
              path: '/repos/$repository/git/blobs',
              body: {'content': base64Encode(bytes), 'encoding': 'base64'},
              expectedStatusCodes: const {201},
            )
            as Map<String, Object?>;
    final sha = json['sha']?.toString();
    if (sha == null || sha.isEmpty) {
      throw const TrackStateProviderException(
        'GitHub blob creation did not return a blob SHA.',
      );
    }
    return sha;
  }

  Future<String> _createTree({
    required String repository,
    required String baseTreeSha,
    required List<Map<String, Object?>> entries,
  }) async {
    final json =
        await _sendGitHubJson(
              method: 'POST',
              path: '/repos/$repository/git/trees',
              body: {'base_tree': baseTreeSha, 'tree': entries},
              expectedStatusCodes: const {201},
            )
            as Map<String, Object?>;
    final sha = json['sha']?.toString();
    if (sha == null || sha.isEmpty) {
      throw const TrackStateProviderException(
        'GitHub tree creation did not return a tree SHA.',
      );
    }
    return sha;
  }

  Future<String> _createGitCommit({
    required String repository,
    required String message,
    required String treeSha,
    required String parentCommitSha,
  }) async {
    final json =
        await _sendGitHubJson(
              method: 'POST',
              path: '/repos/$repository/git/commits',
              body: {
                'message': message,
                'tree': treeSha,
                'parents': [parentCommitSha],
              },
              expectedStatusCodes: const {201},
            )
            as Map<String, Object?>;
    final sha = json['sha']?.toString();
    if (sha == null || sha.isEmpty) {
      throw const TrackStateProviderException(
        'GitHub commit creation did not return a commit SHA.',
      );
    }
    return sha;
  }

  Future<void> _updateGitRef({
    required String repository,
    required String ref,
    required String commitSha,
  }) async {
    await _sendGitHubJson(
      method: 'PATCH',
      path: '/repos/$repository/git/refs/$ref',
      body: {'sha': commitSha, 'force': false},
    );
  }

  Future<Object?> _sendGitHubJson({
    required String method,
    required String path,
    Object? body,
    Set<int> expectedStatusCodes = const {200},
  }) async {
    final response = await _http.send(
      http.Request(method, _githubUri(path))
        ..headers.addAll({
          ..._githubHeaders(_connection?.token),
          if (body != null) 'content-type': 'application/json; charset=utf-8',
        })
        ..body = body == null ? '' : jsonEncode(body),
    );
    final materialized = await http.Response.fromStream(response);
    if (!expectedStatusCodes.contains(materialized.statusCode)) {
      throw TrackStateProviderException(
        'GitHub API request failed for $path '
        '(${materialized.statusCode}): ${materialized.body}',
      );
    }
    return jsonDecode(materialized.body);
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
    attachmentUploadMode: canWrite
        ? AttachmentUploadMode.noLfs
        : AttachmentUploadMode.none,
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

_LfsPointerInfo? _parseLfsPointer(String content) {
  if (!content.contains('version https://git-lfs.github.com/spec/v1')) {
    return null;
  }
  final oidMatch = RegExp(
    r'^oid sha256:([a-f0-9]+)$',
    multiLine: true,
  ).firstMatch(content);
  final sizeMatch = RegExp(r'^size (\d+)$', multiLine: true).firstMatch(content);
  return _LfsPointerInfo(
    oid: oidMatch?.group(1),
    sizeBytes: int.tryParse(sizeMatch?.group(1) ?? ''),
  );
}

class _LfsPointerInfo {
  const _LfsPointerInfo({this.oid, this.sizeBytes});

  final String? oid;
  final int? sizeBytes;
}
