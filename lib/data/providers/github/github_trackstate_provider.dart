import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../domain/models/trackstate_models.dart';
import '../trackstate_provider.dart';

class GitHubTrackStateProvider
    implements
        TrackStateProviderAdapter,
        RepositoryReleaseAttachmentStore,
        RepositoryUserLookup,
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
      _throwGitHubResponseException(
        path: '/repos/${connection.repository}',
        response: repoResponse,
        prefix: 'GitHub connection failed',
      );
    }
    final userJson =
        await _getGitHubJson('/user', token: connection.token)
            as Map<String, Object?>;
    _connection = connection;
    return RepositoryUser(
      login: userJson['login']?.toString() ?? 'github',
      displayName: userJson['name']?.toString() ?? '',
      accountId: userJson['id']?.toString(),
      emailAddress: userJson['email']?.toString(),
      active: true,
    );
  }

  @override
  Future<RepositoryUser> lookupUserByLogin(String login) async {
    final connection = _requireConnection();
    final userJson =
        await _getGitHubJson('/users/$login', token: connection.token)
            as Map<String, Object?>;
    return RepositoryUser(
      login: userJson['login']?.toString() ?? login,
      displayName: userJson['name']?.toString() ?? '',
      accountId: userJson['id']?.toString(),
      emailAddress: userJson['email']?.toString(),
      active: userJson['suspended_at'] == null,
    );
  }

  @override
  Future<RepositoryUser> lookupUserByEmail(String email) async {
    final connection = _requireConnection();
    final searchJson =
        await _getGitHubJson(
              '/search/users',
              queryParameters: {'q': '${email.trim()} in:email'},
              token: connection.token,
            )
            as Map<String, Object?>;
    final items = searchJson['items'];
    if (items is! List<Object?> || items.isEmpty) {
      throw TrackStateProviderException('User was not found for email $email.');
    }
    final match = items.first;
    if (match is! Map<String, Object?>) {
      throw TrackStateProviderException('User was not found for email $email.');
    }
    final login = match['login']?.toString().trim() ?? '';
    if (login.isEmpty) {
      throw TrackStateProviderException('User was not found for email $email.');
    }
    return lookupUserByLogin(login);
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
      _throwGitHubResponseException(
        path: '/repos/$repositoryName/branches/$name',
        response: response,
        prefix: 'GitHub branch lookup failed for $name',
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
      _throwGitHubResponseException(
        path: '/repos/${connection.repository}/contents/${request.path}',
        response: response,
        prefix: 'Could not save ${request.path}',
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
        supportsReleaseAttachmentWrites: false,
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
    var bytes = Uint8List.fromList(base64Decode(encoded));
    final pointerInfo = _parseLfsPointerBytes(bytes);
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
  Future<RepositoryAttachment> readReleaseAttachment(
    RepositoryReleaseAttachmentReadRequest request,
  ) async => readReleaseAttachmentForRepository(
    repository: _requireConnection().repository,
    request: request,
    token: _connection?.token,
  );

  Future<RepositoryAttachment> readReleaseAttachmentForRepository({
    required String repository,
    required RepositoryReleaseAttachmentReadRequest request,
    String? token,
  }) async {
    final requestedAssetId = request.assetId?.trim() ?? '';
    if (requestedAssetId.isNotEmpty) {
      final directArtifact = await _downloadReleaseAsset(
        repository: repository,
        releaseTag: request.releaseTag,
        assetId: requestedAssetId,
        assetName: request.assetName,
        token: token,
        allowMissing: true,
      );
      if (directArtifact != null) {
        return directArtifact;
      }
    }
    final release = (await _loadReleaseByTag(
      repository: repository,
      releaseTag: request.releaseTag,
      issueKey: null,
      expectedTitle: null,
      token: token,
    ))!;
    final matchingAssets = release.assets.where(
      (candidate) => candidate.name == request.assetName,
    );
    final matchedAsset = matchingAssets.isEmpty ? null : matchingAssets.first;
    if (matchedAsset == null) {
      throw TrackStateProviderException(
        'GitHub release ${request.releaseTag} does not contain asset '
        '${request.assetName}.',
      );
    }
    return (await _downloadReleaseAsset(
      repository: repository,
      releaseTag: request.releaseTag,
      assetId: matchedAsset.id,
      assetName: request.assetName,
      expectedSizeBytes: matchedAsset.sizeBytes,
      token: token,
    ))!;
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
  Future<RepositoryReleaseAttachmentWriteResult> writeReleaseAttachment(
    RepositoryReleaseAttachmentWriteRequest request,
  ) async {
    final connection = _requireConnection();
    final release = await _findOrCreateReleaseContainer(
      repository: connection.repository,
      issueKey: request.issueKey,
      releaseTag: request.releaseTag,
      releaseTitle: request.releaseTitle,
      branch: request.branch,
      allowedAssetNames: {...request.allowedAssetNames, request.assetName},
    );
    final existingAsset = release.assets.where(
      (asset) => asset.name == request.assetName,
    );
    if (existingAsset.isNotEmpty) {
      await _deleteReleaseAsset(
        repository: connection.repository,
        releaseTag: request.releaseTag,
        assetId: existingAsset.first.id,
        assetName: existingAsset.first.name,
      );
    }
    final assetId = await _uploadReleaseAsset(
      repository: connection.repository,
      releaseId: release.id,
      releaseTag: request.releaseTag,
      assetName: request.assetName,
      mediaType: request.mediaType,
      bytes: request.bytes,
    );
    return RepositoryReleaseAttachmentWriteResult(
      releaseTag: request.releaseTag,
      assetName: request.assetName,
      assetId: assetId,
    );
  }

  @override
  Future<void> deleteReleaseAttachment(
    RepositoryReleaseAttachmentDeleteRequest request,
  ) async {
    final connection = _requireConnection();
    await _deleteReleaseAsset(
      repository: connection.repository,
      releaseTag: request.releaseTag,
      assetId: request.assetId,
      assetName: request.assetName,
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
              queryParameters: {'sha': ref, 'path': path, 'per_page': '$limit'},
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
      final authorJson =
          commitJson['author'] as Map<String, Object?>? ?? const {};
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

  Future<_GitHubReleaseSummary> _findOrCreateReleaseContainer({
    required String repository,
    required String issueKey,
    required String releaseTag,
    required String releaseTitle,
    required String branch,
    required Set<String> allowedAssetNames,
  }) async {
    final existing = await _loadReleaseByTag(
      repository: repository,
      releaseTag: releaseTag,
      issueKey: issueKey,
      expectedTitle: releaseTitle,
      allowMissing: true,
    );
    if (existing != null) {
      _ensureAllowedReleaseAssets(
        release: existing,
        releaseTag: releaseTag,
        allowedAssetNames: allowedAssetNames,
      );
      return existing;
    }
    final created = await _createReleaseContainer(
      repository: repository,
      issueKey: issueKey,
      releaseTag: releaseTag,
      releaseTitle: releaseTitle,
      branch: branch,
    );
    _ensureAllowedReleaseAssets(
      release: created,
      releaseTag: releaseTag,
      allowedAssetNames: allowedAssetNames,
    );
    return created;
  }

  Future<_GitHubReleaseSummary?> _loadReleaseByTag({
    required String repository,
    required String releaseTag,
    required String? issueKey,
    required String? expectedTitle,
    String? token,
    bool allowMissing = false,
  }) async {
    final response = await _http.get(
      _githubUri('/repos/$repository/releases/tags/$releaseTag'),
      headers: _githubHeaders(token ?? _connection?.token),
    );
    if (response.statusCode == 404) {
      final listedRelease = await _loadReleaseFromList(
        repository: repository,
        releaseTag: releaseTag,
        issueKey: issueKey,
        expectedTitle: expectedTitle,
      );
      if (listedRelease != null) {
        return listedRelease;
      }
      if (allowMissing) {
        return null;
      }
      throw TrackStateProviderException(
        'GitHub release $releaseTag was not found for attachment download.',
      );
    }
    if (response.statusCode != 200) {
      _throwGitHubResponseException(
        path: '/repos/$repository/releases/tags/$releaseTag',
        response: response,
        prefix:
            'Could not resolve GitHub release $releaseTag'
            '${issueKey == null ? '' : ' for issue $issueKey'}',
      );
    }
    final json = jsonDecode(response.body) as Map<String, Object?>;
    return _validateReleaseIdentity(
      _parseReleaseSummary(json, fallbackTagName: releaseTag),
      releaseTag: releaseTag,
      issueKey: issueKey,
      expectedTitle: expectedTitle,
    );
  }

  Future<_GitHubReleaseSummary?> _loadReleaseFromList({
    required String repository,
    required String releaseTag,
    required String? issueKey,
    required String? expectedTitle,
  }) async {
    for (var page = 1; page <= 10; page++) {
      final json = await _getGitHubJson(
            '/repos/$repository/releases',
            queryParameters: {'per_page': '100', 'page': '$page'},
          )
          as List<Object?>;
      final matching = [
        for (final entry in json.whereType<Map<String, Object?>>())
          _parseReleaseSummary(entry, fallbackTagName: releaseTag),
      ].where((release) => release.tagName == releaseTag).toList(growable: false);
      if (matching.length > 1) {
        throw TrackStateProviderException(
          'GitHub release $releaseTag maps to multiple release containers and '
          'requires manual cleanup.',
        );
      }
      if (matching.length == 1) {
        return _validateReleaseIdentity(
          matching.single,
          releaseTag: releaseTag,
          issueKey: issueKey,
          expectedTitle: expectedTitle,
        );
      }
      if (json.length < 100) {
        break;
      }
    }
    return null;
  }

  _GitHubReleaseSummary _validateReleaseIdentity(
    _GitHubReleaseSummary release, {
    required String releaseTag,
    required String? issueKey,
    required String? expectedTitle,
  }) {
    if (expectedTitle != null && release.title != expectedTitle) {
      throw TrackStateProviderException(
        'GitHub release $releaseTag does not match issue '
        '${issueKey ?? releaseTag} and requires manual cleanup.',
      );
    }
    return release;
  }

  Future<_GitHubReleaseSummary> _createReleaseContainer({
    required String repository,
    required String issueKey,
    required String releaseTag,
    required String releaseTitle,
    required String branch,
  }) async {
    final response = await _http.post(
      _githubUri('/repos/$repository/releases'),
      headers: {
        ..._githubHeaders(_connection?.token),
        'content-type': 'application/json; charset=utf-8',
      },
      body: jsonEncode({
        'tag_name': releaseTag,
        'target_commitish': branch,
        'name': releaseTitle,
        'body': _releaseBodyForIssue(issueKey),
        'draft': true,
        'prerelease': false,
      }),
    );
    if (response.statusCode == 403 || response.statusCode == 404) {
      throw TrackStateProviderException(
        'GitHub Releases attachment storage requires permission to manage '
        'releases in $repository.',
      );
    }
    if (response.statusCode == 422) {
      throw TrackStateProviderException(
        'GitHub release $releaseTag could not be created for issue $issueKey. '
        'Resolve the existing tag or release conflict and try again.',
      );
    }
    if (response.statusCode != 201) {
      _throwGitHubResponseException(
        path: '/repos/$repository/releases',
        response: response,
        prefix:
            'Could not create GitHub release $releaseTag for issue $issueKey',
      );
    }
    return _parseReleaseSummary(
      jsonDecode(response.body) as Map<String, Object?>,
      fallbackTagName: releaseTag,
    );
  }

  void _ensureAllowedReleaseAssets({
    required _GitHubReleaseSummary release,
    required String releaseTag,
    required Set<String> allowedAssetNames,
  }) {
    final unexpected = release.assets
        .where((asset) => !allowedAssetNames.contains(asset.name))
        .map((asset) => asset.name)
        .toList(growable: false);
    if (unexpected.isEmpty) {
      return;
    }
    throw TrackStateProviderException(
      'GitHub release $releaseTag contains unexpected assets and requires '
      'manual cleanup: ${unexpected.join(', ')}.',
    );
  }

  Future<void> _deleteReleaseAsset({
    required String repository,
    required String releaseTag,
    required String assetId,
    required String assetName,
  }) async {
    final response = await _http.delete(
      _githubUri('/repos/$repository/releases/assets/$assetId'),
      headers: _githubHeaders(_connection?.token),
    );
    if (response.statusCode != 204) {
      _throwGitHubResponseException(
        path: '/repos/$repository/releases/assets/$assetId',
        response: response,
        prefix:
            'Could not replace GitHub release asset $assetName in $releaseTag',
      );
    }
  }

  Future<String> _uploadReleaseAsset({
    required String repository,
    required String releaseId,
    required String releaseTag,
    required String assetName,
    required String mediaType,
    required Uint8List bytes,
  }) async {
    final response = await _http.send(
      http.Request(
          'POST',
          _githubUploadUri('/repos/$repository/releases/$releaseId/assets', {
            'name': assetName,
          }),
        )
        ..headers.addAll({
          ..._githubHeaders(_connection?.token),
          'content-type': mediaType,
        })
        ..bodyBytes = bytes,
    );
    final materialized = await http.Response.fromStream(response);
    if (materialized.statusCode == 403 || materialized.statusCode == 404) {
      throw TrackStateProviderException(
        'GitHub Releases attachment storage requires permission to upload '
        'assets in $repository.',
      );
    }
    if (materialized.statusCode != 201) {
      _throwGitHubResponseException(
        path: '/repos/$repository/releases/$releaseId/assets',
        response: materialized,
        prefix:
            'Could not upload GitHub release asset $assetName to $releaseTag',
      );
    }
    final json = jsonDecode(materialized.body) as Map<String, Object?>;
    final assetId = json['id']?.toString();
    if (assetId == null || assetId.isEmpty) {
      throw TrackStateProviderException(
        'GitHub release asset upload for $assetName did not return an asset id.',
      );
    }
    return assetId;
  }

  _GitHubReleaseSummary _parseReleaseSummary(
    Map<String, Object?> json, {
    required String fallbackTagName,
  }) {
    final releaseId = json['id']?.toString();
    if (releaseId == null || releaseId.isEmpty) {
      throw const TrackStateProviderException(
        'GitHub release response did not contain a release id.',
      );
    }
    final parsedTagName = json['tag_name']?.toString().trim() ?? '';
    final tagName = parsedTagName.isEmpty ? fallbackTagName : parsedTagName;
    final title = json['name']?.toString().trim() ?? '';
    final assetsJson = json['assets'] as List<Object?>? ?? const <Object?>[];
    return _GitHubReleaseSummary(
      id: releaseId,
      tagName: tagName,
      title: title,
      assets: [
        for (final entry in assetsJson.whereType<Map<String, Object?>>())
          _parseReleaseAsset(entry),
      ],
    );
  }

  _GitHubReleaseAsset _parseReleaseAsset(Map<String, Object?> json) {
    final assetId = json['id']?.toString();
    final name = json['name']?.toString().trim() ?? '';
    if (assetId == null || assetId.isEmpty || name.isEmpty) {
      throw TrackStateProviderException(
        'GitHub release asset response was incomplete: $json',
      );
    }
    return _GitHubReleaseAsset(
      id: assetId,
      name: name,
      sizeBytes: switch (json['size']) {
        final num value => value.toInt(),
        final String value => int.tryParse(value) ?? 0,
        _ => 0,
      },
    );
  }

  String _releaseBodyForIssue(String issueKey) =>
      'TrackState-managed attachment container for $issueKey.\n';

  Future<RepositoryAttachment?> _downloadReleaseAsset({
    required String repository,
    required String releaseTag,
    required String assetId,
    required String assetName,
    String? token,
    int? expectedSizeBytes,
    bool allowMissing = false,
  }) async {
    final response = await _http.get(
      _githubUri('/repos/$repository/releases/assets/$assetId'),
      headers: {
        ..._githubHeaders(token ?? _connection?.token),
        'accept': 'application/octet-stream',
      },
    );
    if (response.statusCode == 404 && allowMissing) {
      return null;
    }
    if (_isRedirectStatus(response.statusCode)) {
      final location = response.headers['location']?.trim() ?? '';
      if (location.isEmpty) {
        throw TrackStateProviderException(
          'GitHub release asset download for $assetName did not return a redirect location.',
        );
      }
      final redirected = await _http.get(Uri.parse(location));
      if (redirected.statusCode == 404 && allowMissing) {
        return null;
      }
      if (redirected.statusCode != 200) {
        _throwGitHubResponseException(
          path: location,
          response: redirected,
          prefix:
              'Could not download GitHub release asset $assetName from '
              '$releaseTag',
        );
      }
      return RepositoryAttachment(
        path: assetName,
        bytes: redirected.bodyBytes,
        revision: assetId,
        declaredSizeBytes: expectedSizeBytes,
      );
    }
    if (response.statusCode != 200) {
      _throwGitHubResponseException(
        path: '/repos/$repository/releases/assets/$assetId',
        response: response,
        prefix:
            'Could not download GitHub release asset $assetName from '
            '$releaseTag',
      );
    }
    return RepositoryAttachment(
      path: assetName,
      bytes: response.bodyBytes,
      revision: assetId,
      declaredSizeBytes: expectedSizeBytes,
    );
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
      _throwGitHubResponseException(
        path: path,
        response: materialized,
        prefix: 'GitHub API request failed for $path',
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
      _throwGitHubResponseException(
        path: path,
        response: response,
        prefix: 'GitHub API request failed for $path',
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

  Never _throwGitHubResponseException({
    required String path,
    required http.Response response,
    required String prefix,
  }) {
    if (_isGitHubRateLimitResponse(response)) {
      throw GitHubRateLimitException(
        message: '$prefix (${response.statusCode}): ${response.body}',
        requestPath: path,
        statusCode: response.statusCode,
        retryAfter: _githubRetryAfter(response),
      );
    }
    throw TrackStateProviderException(
      '$prefix (${response.statusCode}): ${response.body}',
    );
  }

  bool _isGitHubRateLimitResponse(http.Response response) {
    if (response.statusCode != 403 && response.statusCode != 429) {
      return false;
    }
    final body = response.body.toLowerCase();
    return response.headers['x-ratelimit-remaining'] == '0' ||
        body.contains('rate limit exceeded') ||
        body.contains('secondary rate limit');
  }

  DateTime? _githubRetryAfter(http.Response response) {
    final retryAfter = response.headers['retry-after'];
    if (retryAfter != null) {
      final seconds = int.tryParse(retryAfter);
      if (seconds != null) {
        return DateTime.now().toUtc().add(Duration(seconds: seconds));
      }
    }
    final reset = response.headers['x-ratelimit-reset'];
    final resetSeconds = int.tryParse(reset ?? '');
    if (resetSeconds == null) {
      return null;
    }
    return DateTime.fromMillisecondsSinceEpoch(
      resetSeconds * 1000,
      isUtc: true,
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
      supportsReleaseAttachmentWrites: false,
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
    supportsReleaseAttachmentWrites: canWrite,
  );
}

Map<String, String> _githubHeaders(String? token) => {
  'accept': 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
  if (token != null && token.isNotEmpty) 'authorization': 'Bearer $token',
};

Uri _githubUri(String path, [Map<String, String>? queryParameters]) =>
    Uri.https('api.github.com', path, queryParameters);

Uri _githubUploadUri(String path, [Map<String, String>? queryParameters]) =>
    Uri.https('uploads.github.com', path, queryParameters);

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

_LfsPointerInfo? _parseLfsPointerBytes(Uint8List bytes) {
  const pointerPrefix = 'version https://git-lfs.github.com/spec/v1';
  if (bytes.length < pointerPrefix.length || bytes.length > 512) {
    return null;
  }
  for (var index = 0; index < pointerPrefix.length; index++) {
    if (bytes[index] != pointerPrefix.codeUnitAt(index)) {
      return null;
    }
  }
  for (final byte in bytes) {
    final isWhitespace = byte == 0x09 || byte == 0x0A || byte == 0x0D;
    final isPrintableAscii = byte >= 0x20 && byte <= 0x7E;
    if (!isWhitespace && !isPrintableAscii) {
      return null;
    }
  }
  return _parseLfsPointer(ascii.decode(bytes));
}

_LfsPointerInfo? _parseLfsPointer(String content) {
  if (!content.contains('version https://git-lfs.github.com/spec/v1')) {
    return null;
  }
  final oidMatch = RegExp(
    r'^oid sha256:([a-f0-9]+)$',
    multiLine: true,
  ).firstMatch(content);
  final sizeMatch = RegExp(
    r'^size (\d+)$',
    multiLine: true,
  ).firstMatch(content);
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

class _GitHubReleaseSummary {
  const _GitHubReleaseSummary({
    required this.id,
    required this.tagName,
    required this.title,
    required this.assets,
  });

  final String id;
  final String tagName;
  final String title;
  final List<_GitHubReleaseAsset> assets;
}

class _GitHubReleaseAsset {
  const _GitHubReleaseAsset({
    required this.id,
    required this.name,
    required this.sizeBytes,
  });

  final String id;
  final String name;
  final int sizeBytes;
}

bool _isRedirectStatus(int statusCode) =>
    statusCode == 301 ||
    statusCode == 302 ||
    statusCode == 303 ||
    statusCode == 307 ||
    statusCode == 308;
