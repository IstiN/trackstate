import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../domain/models/trackstate_models.dart';
import '../providers/github/github_trackstate_provider.dart';
import '../providers/trackstate_provider.dart';

abstract interface class TrackStateRepository {
  bool get usesLocalPersistence;
  bool get supportsGitHubAuth;
  Future<TrackerSnapshot> loadSnapshot();
  Future<List<TrackStateIssue>> searchIssues(String jql);
  Future<RepositoryUser> connect(RepositoryConnection connection);
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  );
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  );
}

class ProviderBackedTrackStateRepository implements TrackStateRepository {
  static const RepositoryPermission _restrictedPermission =
      RepositoryPermission(
        canRead: false,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        canCheckCollaborators: false,
      );

  ProviderBackedTrackStateRepository({
    required TrackStateProviderAdapter provider,
    this.usesLocalPersistence = false,
    this.supportsGitHubAuth = true,
  }) : _provider = provider,
       _session = ProviderSession(
         providerType: provider.providerType,
         connectionState: ProviderConnectionState.disconnected,
         resolvedUserIdentity: provider.repositoryLabel,
         canRead: _restrictedPermission.canRead,
         canWrite: _restrictedPermission.canWrite,
         canCreateBranch: _restrictedPermission.canCreateBranch,
         canManageAttachments: _restrictedPermission.canManageAttachments,
         canCheckCollaborators: _restrictedPermission.canCheckCollaborators,
       );

  final TrackStateProviderAdapter _provider;
  @override
  final bool usesLocalPersistence;
  @override
  final bool supportsGitHubAuth;
  TrackerSnapshot? _snapshot;
  ProviderSession? _session;

  ProviderSession? get session => _session;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    RepositoryPermission initialPermission = _restrictedPermission;
    try {
      initialPermission = await _provider.getPermission();
    } catch (_) {
      initialPermission = _restrictedPermission;
    }
    _session = ProviderSession(
      providerType: _provider.providerType,
      connectionState: ProviderConnectionState.connecting,
      resolvedUserIdentity: _provider.repositoryLabel,
      canRead: initialPermission.canRead,
      canWrite: initialPermission.canWrite,
      canCreateBranch: initialPermission.canCreateBranch,
      canManageAttachments: initialPermission.canManageAttachments,
      canCheckCollaborators: initialPermission.canCheckCollaborators,
    );
    _syncProviderSession(
      connectionState: ProviderConnectionState.connecting,
      resolvedUserIdentity: _provider.repositoryLabel,
      permission: initialPermission,
    );

    RepositoryUser? user;
    try {
      user = await _provider.authenticate(connection);
      final permission = await _provider.getPermission();
      _syncProviderSession(
        connectionState: ProviderConnectionState.connected,
        resolvedUserIdentity: _resolveUserIdentity(user),
        permission: permission,
      );
      return user;
    } catch (_) {
      _syncProviderSession(
        connectionState: ProviderConnectionState.disconnected,
        resolvedUserIdentity: _resolveUserIdentity(user),
        permission: _restrictedPermission,
      );
      rethrow;
    }
  }

  String _resolveUserIdentity(RepositoryUser? user) {
    if (user == null) {
      return _provider.repositoryLabel;
    }
    if (user.login.isNotEmpty) {
      return user.login;
    }
    if (user.displayName.isNotEmpty) {
      return user.displayName;
    }
    return _provider.repositoryLabel;
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await _loadSetupSnapshot();
    _snapshot = snapshot;
    return snapshot;
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async {
    final snapshot = _snapshot ?? await loadSnapshot();
    return _filterIssues(snapshot.issues, jql);
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot be saved.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final normalizedDescription = description.trim();
    final writeBranch = await _provider.resolveWriteBranch();
    final file = await _provider.readTextFile(
      issue.storagePath,
      ref: writeBranch,
    );
    final updatedMarkdown = _replaceSection(
      file.content,
      'Description',
      normalizedDescription,
    );
    await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: issue.storagePath,
        content: updatedMarkdown,
        message: 'Update ${issue.key} description',
        branch: writeBranch,
        expectedRevision: file.revision,
      ),
    );

    final updatedIssue = issue.copyWith(
      description: normalizedDescription,
      rawMarkdown: updatedMarkdown,
      updatedLabel: 'just now',
    );
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot be saved.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final writeBranch = await _provider.resolveWriteBranch();
    final file = await _provider.readTextFile(
      issue.storagePath,
      ref: writeBranch,
    );
    final statusId = await _resolveStatusIdForUpdate(
      issue: issue,
      status: status,
      writeBranch: writeBranch,
    );
    final updatedMarkdown = _replaceFrontmatterValue(
      file.content,
      'status',
      statusId,
    );
    await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: issue.storagePath,
        content: updatedMarkdown,
        message: 'Move ${issue.key} to ${status.label}',
        branch: writeBranch,
        expectedRevision: file.revision,
      ),
    );

    final updatedIssue = issue.copyWith(
      status: status,
      statusId: statusId,
      rawMarkdown: updatedMarkdown,
      updatedLabel: 'just now',
    );
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  Future<TrackerSnapshot> _loadSetupSnapshot() async {
    final tree = await _provider.listTree(ref: _provider.dataRef);
    final blobPaths = tree
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    final projectPath = blobPaths.firstWhere(
      (path) => path.endsWith('/project.json') || path == 'project.json',
      orElse: () => throw const TrackStateRepositoryException(
        'project.json was not found in the repository.',
      ),
    );
    final dataRoot = projectPath.contains('/')
        ? projectPath.substring(0, projectPath.lastIndexOf('/'))
        : '';
    final projectJson =
        await _getRepositoryJson(projectPath) as Map<String, Object?>;
    final configRoot = _resolveConfigRoot(projectJson, dataRoot);
    final defaultLocale = projectJson['defaultLocale']?.toString() ?? 'en';
    final localizedLabels = await _loadLocalizedLabels(
      blobPaths: blobPaths,
      configRoot: configRoot,
      locale: defaultLocale,
    );
    final issueTypes = await _getConfigEntries(
      _joinPath(configRoot, 'issue-types.json'),
      localizedLabels: localizedLabels['issueTypes'] ?? const {},
      locale: defaultLocale,
    );
    final statuses = await _getConfigEntries(
      _joinPath(configRoot, 'statuses.json'),
      localizedLabels: localizedLabels['statuses'] ?? const {},
      locale: defaultLocale,
    );
    final fields = await _getFieldDefinitions(
      _joinPath(configRoot, 'fields.json'),
      localizedLabels: localizedLabels['fields'] ?? const {},
      locale: defaultLocale,
    );
    final priorities = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'priorities.json'),
      localizedLabels: localizedLabels['priorities'] ?? const {},
      locale: defaultLocale,
    );
    final versions = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'versions.json'),
      localizedLabels: localizedLabels['versions'] ?? const {},
      locale: defaultLocale,
    );
    final components = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'components.json'),
      localizedLabels: localizedLabels['components'] ?? const {},
      locale: defaultLocale,
    );
    final resolutions = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'resolutions.json'),
      localizedLabels: localizedLabels['resolutions'] ?? const {},
      locale: defaultLocale,
    );
    final repositoryIndex = await _loadRepositoryIndex(
      blobPaths: blobPaths,
      dataRoot: dataRoot,
      issueTypeDefinitions: issueTypes,
    );
    final issuePaths =
        repositoryIndex.entries.isNotEmpty
              ? repositoryIndex.entries.map((entry) => entry.path).toList()
              : tree
                    .where(
                      (entry) =>
                          entry.type == 'blob' &&
                          entry.path.startsWith(
                            dataRoot.isEmpty ? '' : '$dataRoot/',
                          ) &&
                          entry.path.endsWith('/main.md'),
                    )
                    .map((entry) => entry.path)
                    .toList()
          ..sort();
    if (issuePaths.isEmpty) {
      throw TrackStateRepositoryException(
        'No issue markdown files were found under ${dataRoot.isEmpty ? 'repository root' : dataRoot}.',
      );
    }

    final indexEntriesByPath = {
      for (final entry in repositoryIndex.entries) entry.path: entry,
    };
    final issues = <TrackStateIssue>[];
    for (final path in issuePaths..sort()) {
      final markdown = await _getRepositoryText(path);
      final issueRoot = path.substring(0, path.lastIndexOf('/'));
      final acceptancePath = _joinPath(issueRoot, 'acceptance_criteria.md');
      final acceptance = blobPaths.contains(acceptancePath)
          ? await _getRepositoryText(acceptancePath)
          : null;
      final comments = await _loadComments(
        blobPaths: blobPaths,
        issueRoot: issueRoot,
      );
      final links = await _loadLinks(
        blobPaths: blobPaths,
        issueRoot: issueRoot,
      );
      final attachments = _loadAttachments(tree: tree, issueRoot: issueRoot);
      issues.add(
        _parseIssue(
          storagePath: path,
          markdown: markdown,
          acceptanceMarkdown: acceptance,
          comments: comments,
          links: links,
          attachments: attachments,
          repositoryIndexEntry: indexEntriesByPath[path],
          issueTypeDefinitions: issueTypes,
          statusDefinitions: statuses,
          priorityDefinitions: priorities,
          resolutionDefinitions: resolutions,
        ),
      );
    }
    issues.sort((a, b) => a.key.compareTo(b.key));

    final normalizedIndex = _normalizeRepositoryIndex(
      repositoryIndex.entries.isEmpty
          ? _deriveRepositoryIndex(issues, repositoryIndex.deleted)
          : repositoryIndex,
      issues,
    );
    final indexedIssues = [
      for (final issue in issues)
        issue.withRepositoryIndex(normalizedIndex.entryForKey(issue.key)),
    ]..sort((a, b) => a.key.compareTo(b.key));

    final project = ProjectConfig(
      key: (projectJson['key'] as String?) ?? 'DEMO',
      name: (projectJson['name'] as String?) ?? 'TrackState Project',
      repository: _provider.repositoryLabel,
      branch: await _provider.resolveWriteBranch(),
      defaultLocale: defaultLocale,
      issueTypeDefinitions: issueTypes,
      statusDefinitions: statuses,
      fieldDefinitions: fields,
      priorityDefinitions: priorities,
      versionDefinitions: versions,
      componentDefinitions: components,
      resolutionDefinitions: resolutions,
    );
    return TrackerSnapshot(
      project: project,
      issues: indexedIssues,
      repositoryIndex: normalizedIndex,
    );
  }

  ProviderSession _syncProviderSession({
    required ProviderConnectionState connectionState,
    required String resolvedUserIdentity,
    required RepositoryPermission permission,
  }) {
    final session =
        _session ??
        ProviderSession(
          providerType: _provider.providerType,
          connectionState: connectionState,
          resolvedUserIdentity: resolvedUserIdentity,
          canRead: permission.canRead,
          canWrite: permission.canWrite,
          canCreateBranch: permission.canCreateBranch,
          canManageAttachments: permission.canManageAttachments,
          canCheckCollaborators: permission.canCheckCollaborators,
        );
    session.update(
      providerType: _provider.providerType,
      connectionState: connectionState,
      resolvedUserIdentity: resolvedUserIdentity,
      canRead: permission.canRead,
      canWrite: permission.canWrite,
      canCreateBranch: permission.canCreateBranch,
      canManageAttachments: permission.canManageAttachments,
      canCheckCollaborators: permission.canCheckCollaborators,
    );
    _session = session;
    return session;
  }

  String _resolveConfigRoot(Map<String, Object?> projectJson, String dataRoot) {
    final configuredPath = projectJson['configPath']?.toString().trim();
    if (configuredPath == null || configuredPath.isEmpty) {
      return dataRoot.isEmpty ? 'config' : '$dataRoot/config';
    }
    final normalizedPath = configuredPath
        .replaceFirst(RegExp(r'^/'), '')
        .replaceFirst(RegExp(r'/$'), '');
    if (normalizedPath.isEmpty) {
      return dataRoot.isEmpty ? 'config' : '$dataRoot/config';
    }
    if (dataRoot.isNotEmpty && !normalizedPath.startsWith('$dataRoot/')) {
      return '$dataRoot/$normalizedPath';
    }
    return normalizedPath;
  }

  Future<String> _getRepositoryText(String path) async =>
      (await _provider.readTextFile(path, ref: _provider.dataRef)).content;

  Future<Object?> _getRepositoryJson(String path) async =>
      jsonDecode(await _getRepositoryText(path));

  Future<Map<String, Map<String, String>>> _loadLocalizedLabels({
    required Set<String> blobPaths,
    required String configRoot,
    required String locale,
  }) async {
    final path = _joinPath(configRoot, 'i18n/$locale.json');
    if (!blobPaths.contains(path)) return const {};
    final json = await _getRepositoryJson(path);
    if (json is! Map) return const {};
    final result = <String, Map<String, String>>{};
    for (final entry in json.entries) {
      final value = entry.value;
      if (value is! Map) continue;
      result[entry.key.toString()] = {
        for (final localizedEntry in value.entries)
          localizedEntry.key.toString(): localizedEntry.value.toString(),
      };
    }
    return result;
  }

  Future<List<TrackStateConfigEntry>> _getConfigEntries(
    String path, {
    required Map<String, String> localizedLabels,
    required String locale,
  }) async {
    return _configEntriesFromJson(
      await _getRepositoryJson(path),
      localizedLabels: localizedLabels,
      locale: locale,
    );
  }

  Future<List<TrackStateConfigEntry>> _loadOptionalConfigEntries({
    required Set<String> blobPaths,
    required String path,
    required Map<String, String> localizedLabels,
    required String locale,
  }) async {
    if (!blobPaths.contains(path)) return const [];
    return _getConfigEntries(
      path,
      localizedLabels: localizedLabels,
      locale: locale,
    );
  }

  Future<List<TrackStateFieldDefinition>> _getFieldDefinitions(
    String path, {
    required Map<String, String> localizedLabels,
    required String locale,
  }) async {
    final json = await _getRepositoryJson(path);
    if (json is! List) return const [];
    return json
        .whereType<Map>()
        .map((entry) {
          final rawId = entry['id']?.toString();
          final id = rawId == null || rawId.isEmpty
              ? _canonicalConfigId(entry['name']?.toString())
              : rawId;
          final fallbackName = entry['name']?.toString() ?? id;
          final localizedLabel = localizedLabels[id];
          return TrackStateFieldDefinition(
            id: id,
            name: fallbackName,
            type: entry['type']?.toString() ?? 'string',
            required: entry['required'] == true,
            localizedLabels: localizedLabel == null
                ? const {}
                : {locale: localizedLabel},
          );
        })
        .toList(growable: false);
  }

  Future<RepositoryIndex> _loadRepositoryIndex({
    required Set<String> blobPaths,
    required String dataRoot,
    required List<TrackStateConfigEntry> issueTypeDefinitions,
  }) async {
    final issuesPath = _joinPath(dataRoot, '.trackstate/index/issues.json');
    final deletedPath = _joinPath(dataRoot, '.trackstate/index/deleted.json');
    final entries = <RepositoryIssueIndexEntry>[];
    if (blobPaths.contains(issuesPath)) {
      final json = await _getRepositoryJson(issuesPath);
      if (json is List) {
        entries.addAll(
          json.whereType<Map>().map((entry) => _repositoryIndexEntry(entry)),
        );
      }
    }
    final deleted = <DeletedIssueTombstone>[];
    if (blobPaths.contains(deletedPath)) {
      final json = await _getRepositoryJson(deletedPath);
      if (json is List) {
        deleted.addAll(
          json.whereType<Map>().map(
            (entry) => _deletedIssueTombstone(
              entry,
              issueTypeDefinitions: issueTypeDefinitions,
            ),
          ),
        );
      }
    }
    return RepositoryIndex(entries: entries, deleted: deleted);
  }

  Future<List<IssueComment>> _loadComments({
    required Set<String> blobPaths,
    required String issueRoot,
  }) async {
    final commentPrefix = _joinPath(issueRoot, 'comments/');
    final commentPaths =
        blobPaths
            .where(
              (path) => path.startsWith(commentPrefix) && path.endsWith('.md'),
            )
            .toList()
          ..sort();
    final comments = <IssueComment>[];
    for (final path in commentPaths) {
      comments.add(_parseComment(path, await _getRepositoryText(path)));
    }
    return comments;
  }

  Future<List<IssueLink>> _loadLinks({
    required Set<String> blobPaths,
    required String issueRoot,
  }) async {
    final linksPath = _joinPath(issueRoot, 'links.json');
    if (!blobPaths.contains(linksPath)) return const [];
    final json = await _getRepositoryJson(linksPath);
    if (json is! List) return const [];
    return json
        .whereType<Map>()
        .map(
          (entry) => IssueLink(
            type: entry['type']?.toString() ?? 'relates-to',
            targetKey:
                entry['target']?.toString() ??
                entry['targetKey']?.toString() ??
                '',
            direction: entry['direction']?.toString() ?? 'outward',
          ),
        )
        .where((link) => link.targetKey.isNotEmpty)
        .toList(growable: false);
  }

  List<IssueAttachment> _loadAttachments({
    required List<RepositoryTreeEntry> tree,
    required String issueRoot,
  }) {
    final attachmentPrefix = _joinPath(issueRoot, 'attachments/');
    return tree
        .where(
          (entry) =>
              entry.type == 'blob' &&
              entry.path.startsWith(attachmentPrefix) &&
              entry.path.length > attachmentPrefix.length,
        )
        .map(
          (entry) => IssueAttachment(
            name: entry.path.split('/').last,
            storagePath: entry.path,
            mediaType: _mediaTypeForPath(entry.path),
          ),
        )
        .toList(growable: false)
      ..sort((a, b) => a.name.compareTo(b.name));
  }

  void _replaceCachedIssue(TrackStateIssue updatedIssue) {
    final snapshot = _snapshot;
    if (snapshot == null) return;
    _snapshot = TrackerSnapshot(
      project: snapshot.project,
      repositoryIndex: snapshot.repositoryIndex,
      issues: [
        for (final issue in snapshot.issues)
          if (issue.key == updatedIssue.key) updatedIssue else issue,
      ],
    );
  }

  Future<String> _resolveStatusIdForUpdate({
    required TrackStateIssue issue,
    required IssueStatus status,
    required String writeBranch,
  }) async {
    final statusDefinitions = await _loadConnectedStatusDefinitions(
      storagePath: issue.storagePath,
      ref: writeBranch,
    );
    return _statusIdForStatus(
      status,
      definitions: statusDefinitions,
      currentIssue: issue,
    );
  }

  Future<List<TrackStateConfigEntry>> _loadConnectedStatusDefinitions({
    required String storagePath,
    required String ref,
  }) async {
    final projectRoot = storagePath.split('/').first;
    if (projectRoot.isEmpty) {
      return _snapshot?.project.statusDefinitions ?? const [];
    }

    final path = '$projectRoot/config/statuses.json';
    try {
      final file = await _provider.readTextFile(path, ref: ref);
      return _configEntriesFromJson(
        jsonDecode(file.content),
        localizedLabels: const {},
        locale: 'en',
      );
    } on TrackStateProviderException {
      return _snapshot?.project.statusDefinitions ?? const [];
    }
  }
}

class SetupTrackStateRepository extends ProviderBackedTrackStateRepository {
  SetupTrackStateRepository({
    http.Client? client,
    String repositoryName = GitHubTrackStateProvider.defaultRepositoryName,
    String sourceRef = GitHubTrackStateProvider.defaultSourceRef,
    String dataRef = GitHubTrackStateProvider.defaultDataRef,
  }) : super(
         provider: GitHubTrackStateProvider(
           client: client,
           repositoryName: repositoryName,
           sourceRef: sourceRef,
           dataRef: dataRef,
         ),
       );

  static const repositoryName = GitHubTrackStateProvider.defaultRepositoryName;
  static const sourceRef = GitHubTrackStateProvider.defaultSourceRef;
  static const dataRef = GitHubTrackStateProvider.defaultDataRef;
}

class DemoTrackStateRepository implements TrackStateRepository {
  const DemoTrackStateRepository();

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      _filterIssues(_snapshot.issues, jql);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(
    status: status,
    statusId: _statusIdForStatus(
      status,
      definitions: _project.statusDefinitions,
      currentIssue: issue,
    ),
    updatedLabel: 'just now',
  );
}

class TrackStateRepositoryException extends TrackStateProviderException {
  const TrackStateRepositoryException(super.message);
}

TrackStateIssue _parseIssue({
  required String storagePath,
  required String markdown,
  String? acceptanceMarkdown,
  required List<IssueComment> comments,
  required List<IssueLink> links,
  required List<IssueAttachment> attachments,
  RepositoryIssueIndexEntry? repositoryIndexEntry,
  required List<TrackStateConfigEntry> issueTypeDefinitions,
  required List<TrackStateConfigEntry> statusDefinitions,
  required List<TrackStateConfigEntry> priorityDefinitions,
  required List<TrackStateConfigEntry> resolutionDefinitions,
}) {
  final frontmatter = _frontmatter(markdown);
  final body = _body(markdown);
  final issueTypeId = _resolvedConfigId(
    frontmatter['issueType']?.toString(),
    definitions: issueTypeDefinitions,
  );
  final statusId = _resolvedConfigId(
    frontmatter['status']?.toString(),
    definitions: statusDefinitions,
  );
  final priorityId = _resolvedConfigId(
    frontmatter['priority']?.toString(),
    definitions: priorityDefinitions,
  );
  final issueType = _issueType(issueTypeId, issueTypeDefinitions);
  final status = _issueStatus(statusId, statusDefinitions);
  final priority = _issuePriority(priorityId, priorityDefinitions);
  final description = _section(
    body,
    'Description',
  ).ifEmpty(_section(body, 'Summary'));
  final acceptance = acceptanceMarkdown == null
      ? const <String>[]
      : LineSplitter.split(acceptanceMarkdown)
            .where((line) => line.trimLeft().startsWith('- '))
            .map((line) => line.trimLeft().substring(2).trim())
            .toList(growable: false);
  final frontmatterSummary = frontmatter['summary']?.toString() ?? '';
  final summary = frontmatterSummary
      .ifEmpty(_section(body, 'Summary'))
      .ifEmpty('Untitled issue');

  return TrackStateIssue(
    key: frontmatter['key']?.toString() ?? 'UNKNOWN-0',
    project: frontmatter['project']?.toString() ?? 'DEMO',
    issueType: issueType,
    issueTypeId: issueTypeId,
    status: status,
    statusId: statusId,
    priority: priority,
    priorityId: priorityId,
    summary: summary,
    description: description.ifEmpty(body),
    assignee: frontmatter['assignee']?.toString() ?? 'unassigned',
    reporter: frontmatter['reporter']?.toString() ?? 'unknown',
    labels: _stringList(frontmatter['labels']),
    components: _stringList(frontmatter['components']),
    fixVersionIds: _stringList(frontmatter['fixVersions']),
    watchers: _stringList(frontmatter['watchers']),
    customFields: _customFieldsFromFrontmatter(frontmatter),
    parentKey: _nullable(frontmatter['parent']?.toString()),
    epicKey: _nullable(frontmatter['epic']?.toString()),
    parentPath: repositoryIndexEntry?.parentPath,
    epicPath: repositoryIndexEntry?.epicPath,
    progress: status == IssueStatus.done ? 1 : .35,
    updatedLabel: frontmatter['updated']?.toString() ?? 'from repo',
    acceptanceCriteria: acceptance,
    comments: comments,
    links: links,
    attachments: attachments,
    isArchived:
        _boolValue(frontmatter['archived']) ??
        repositoryIndexEntry?.isArchived ??
        false,
    resolutionId: _nullableResolvedId(
      frontmatter['resolution'],
      definitions: resolutionDefinitions,
    ),
    storagePath: storagePath,
    rawMarkdown: markdown,
  );
}

IssueComment _parseComment(String path, String markdown) {
  final frontmatter = _frontmatter(markdown);
  final body = _body(markdown);
  final createdAt = frontmatter['created']?.toString();
  final updatedAt = frontmatter['updated']?.toString();
  return IssueComment(
    id: path.split('/').last.replaceAll('.md', ''),
    author: frontmatter['author']?.toString() ?? 'unknown',
    body: body,
    createdAt: createdAt,
    updatedAt: updatedAt,
    updatedLabel: updatedAt ?? createdAt ?? 'from repo',
    storagePath: path,
  );
}

Map<String, Object?> _frontmatter(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.isEmpty || lines.first.trim() != '---') return const {};
  final result = <String, Object?>{};
  String? pendingRootKey;
  String? activeRootListKey;
  String? activeMapKey;
  String? pendingMapListKey;

  for (final rawLine in lines.skip(1)) {
    if (rawLine.trim() == '---') break;
    if (rawLine.trim().isEmpty) continue;

    final indent = rawLine.length - rawLine.trimLeft().length;
    final line = rawLine.trimRight();
    final trimmed = line.trimLeft();
    final listItem = RegExp(r'^-\s+(.+)$').firstMatch(trimmed);
    final keyValue = RegExp(r'^([A-Za-z0-9_-]+):\s*(.*)$').firstMatch(trimmed);

    if (indent == 0) {
      pendingRootKey = null;
      activeRootListKey = null;
      activeMapKey = null;
      pendingMapListKey = null;
      if (keyValue == null) continue;
      final key = keyValue.group(1)!;
      final rawValue = keyValue.group(2)!.trim();
      if (rawValue.isEmpty) {
        pendingRootKey = key;
        result[key] = null;
      } else {
        result[key] = _parseScalar(rawValue);
      }
      continue;
    }

    if (indent == 2) {
      if (pendingRootKey != null) {
        if (listItem != null) {
          final list = <Object?>[];
          result[pendingRootKey] = list;
          activeRootListKey = pendingRootKey;
          pendingRootKey = null;
          list.add(_parseScalar(listItem.group(1)!));
          continue;
        }
        if (keyValue != null) {
          final map = <String, Object?>{};
          result[pendingRootKey] = map;
          activeMapKey = pendingRootKey;
          pendingRootKey = null;
          final nestedKey = keyValue.group(1)!;
          final nestedValue = keyValue.group(2)!.trim();
          if (nestedValue.isEmpty) {
            pendingMapListKey = nestedKey;
            map[nestedKey] = null;
          } else {
            map[nestedKey] = _parseScalar(nestedValue);
          }
          continue;
        }
      }
      if (activeRootListKey != null && listItem != null) {
        (result[activeRootListKey] as List<Object?>).add(
          _parseScalar(listItem.group(1)!),
        );
        continue;
      }
      if (activeMapKey != null) {
        final map = result[activeMapKey] as Map<String, Object?>;
        if (keyValue != null) {
          final nestedKey = keyValue.group(1)!;
          final nestedValue = keyValue.group(2)!.trim();
          if (nestedValue.isEmpty) {
            pendingMapListKey = nestedKey;
            map[nestedKey] = null;
          } else {
            pendingMapListKey = null;
            map[nestedKey] = _parseScalar(nestedValue);
          }
          continue;
        }
      }
    }

    if (indent == 4 && activeMapKey != null && pendingMapListKey != null) {
      final map = result[activeMapKey] as Map<String, Object?>;
      if (listItem == null) continue;
      final list = (map[pendingMapListKey] as List<Object?>?) ?? <Object?>[];
      map[pendingMapListKey] = list;
      list.add(_parseScalar(listItem.group(1)!));
    }
  }

  return result;
}

Object? _parseScalar(String value) {
  final trimmed = value.trim();
  if (trimmed == 'null') return null;
  if (trimmed == 'true') return true;
  if (trimmed == 'false') return false;
  if ((trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
    final structuredValue = _parseInlineStructuredValue(trimmed);
    if (structuredValue != null) return structuredValue;
  }
  if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
      (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.substring(1, trimmed.length - 1);
  }
  final intValue = int.tryParse(trimmed);
  if (intValue != null) return intValue;
  final doubleValue = double.tryParse(trimmed);
  if (doubleValue != null) return doubleValue;
  return trimmed;
}

Object? _parseInlineStructuredValue(String value) {
  try {
    return _normalizeStructuredValue(jsonDecode(value));
  } on FormatException {
    return null;
  }
}

Object? _normalizeStructuredValue(Object? value) {
  if (value is List) {
    return value
        .map<Object?>((entry) => _normalizeStructuredValue(entry))
        .toList(growable: false);
  }
  if (value is Map) {
    return {
      for (final entry in value.entries)
        entry.key.toString(): _normalizeStructuredValue(entry.value),
    };
  }
  return value;
}

List<String> _stringList(Object? value) {
  if (value is List) {
    return value.map((entry) => entry.toString()).toList(growable: false);
  }
  if (value == null) return const [];
  return value
      .toString()
      .split('|')
      .map((entry) => entry.trim())
      .where((entry) => entry.isNotEmpty)
      .toList(growable: false);
}

Map<String, Object?> _stringObjectMap(Object? value) {
  if (value is! Map) return const {};
  return {for (final entry in value.entries) entry.key.toString(): entry.value};
}

const Set<String> _issueFrontmatterCoreKeys = {
  'key',
  'project',
  'issueType',
  'status',
  'priority',
  'summary',
  'assignee',
  'reporter',
  'labels',
  'components',
  'fixVersions',
  'watchers',
  'customFields',
  'parent',
  'epic',
  'created',
  'updated',
  'archived',
  'resolution',
};

Map<String, Object?> _customFieldsFromFrontmatter(
  Map<String, Object?> frontmatter,
) {
  final customFields = {..._stringObjectMap(frontmatter['customFields'])};
  for (final entry in frontmatter.entries) {
    if (_issueFrontmatterCoreKeys.contains(entry.key)) continue;
    customFields.putIfAbsent(entry.key, () => entry.value);
  }
  return customFields;
}

bool? _boolValue(Object? value) {
  if (value is bool) return value;
  if (value == null) return null;
  final normalized = value.toString().trim().toLowerCase();
  if (normalized == 'true') return true;
  if (normalized == 'false') return false;
  return null;
}

String? _nullable(String? value) =>
    value == null || value == 'null' || value.isEmpty ? null : value;

String _body(String markdown) {
  final lines = const LineSplitter().convert(markdown);
  if (lines.isEmpty || lines.first.trim() != '---') return markdown.trim();
  final endIndex = lines.indexWhere((line) => line.trim() == '---', 1);
  if (endIndex == -1) return markdown.trim();
  return lines.skip(endIndex + 1).join('\n').trim();
}

String _section(String markdown, String title) {
  final match = RegExp(
    '^# $title\\s*\\n([\\s\\S]*?)(?=\\n# |\\z)',
    multiLine: true,
  ).firstMatch(markdown);
  return match?.group(1)?.trim() ?? '';
}

String _replaceFrontmatterValue(String markdown, String key, String value) {
  final pattern = RegExp('^$key:\\s*.*\$', multiLine: true);
  if (pattern.hasMatch(markdown)) {
    return markdown.replaceFirst(pattern, '$key: $value');
  }
  return markdown.replaceFirst('---\n', '---\n$key: $value\n');
}

String _replaceSection(String markdown, String title, String content) {
  final normalizedContent = content.trim();
  final pattern = RegExp(
    '^# $title\\s*\\n([\\s\\S]*?)(?=\\n# |\\z)',
    multiLine: true,
  );
  if (pattern.hasMatch(markdown)) {
    return markdown.replaceFirst(pattern, '# $title\n\n$normalizedContent');
  }
  final trimmed = markdown.trimRight();
  final separator = trimmed.isEmpty ? '' : '\n\n';
  return '$trimmed$separator# $title\n\n$normalizedContent\n';
}

List<TrackStateConfigEntry> _configEntriesFromJson(
  Object? json, {
  required Map<String, String> localizedLabels,
  required String locale,
}) {
  if (json is! List) return const [];
  return json
      .whereType<Map>()
      .map((entry) {
        final rawId = entry['id']?.toString();
        final id = rawId == null || rawId.isEmpty
            ? _canonicalConfigId(entry['name']?.toString())
            : rawId;
        final fallbackName = entry['name']?.toString() ?? id;
        final localizedLabel = localizedLabels[id];
        return TrackStateConfigEntry(
          id: id,
          name: fallbackName,
          localizedLabels: localizedLabel == null
              ? const {}
              : {locale: localizedLabel},
        );
      })
      .toList(growable: false);
}

IssueType _issueType(
  String? value, [
  List<TrackStateConfigEntry> definitions = const [],
]) => switch (_configSemanticToken(value, definitions)) {
  'epic' => IssueType.epic,
  'subtask' || 'sub-task' => IssueType.subtask,
  'bug' => IssueType.bug,
  'task' => IssueType.task,
  _ => IssueType.story,
};

IssueStatus _issueStatus(
  String? value, [
  List<TrackStateConfigEntry> definitions = const [],
]) {
  final token = _configSemanticToken(value, definitions);
  if (token == 'done' || token.contains('done')) {
    return IssueStatus.done;
  }
  if (token == 'in-review' || token.contains('review')) {
    return IssueStatus.inReview;
  }
  if (token == 'in-progress' || token.contains('progress')) {
    return IssueStatus.inProgress;
  }
  if (token == 'todo' || token == 'to-do' || token.contains('backlog')) {
    return IssueStatus.todo;
  }
  return IssueStatus.todo;
}

IssuePriority _issuePriority(
  String? value, [
  List<TrackStateConfigEntry> definitions = const [],
]) {
  final token = _configSemanticToken(value, definitions);
  if (token == 'highest' || token.contains('highest')) {
    return IssuePriority.highest;
  }
  if (token == 'high' || token.startsWith('high-')) {
    return IssuePriority.high;
  }
  if (token == 'low' || token.contains('low')) {
    return IssuePriority.low;
  }
  return IssuePriority.medium;
}

String _configSemanticToken(
  String? value,
  List<TrackStateConfigEntry> definitions,
) {
  final text = (value ?? '').trim();
  if (text.isEmpty) return '';
  final match = _matchingConfigEntry(text, definitions);
  final semanticSource = match?.name ?? text;
  final normalized = _canonicalConfigId(semanticSource);
  if (normalized.isNotEmpty) return normalized;
  return _canonicalConfigId(match?.id ?? text);
}

TrackStateConfigEntry? _matchingConfigEntry(
  String value,
  List<TrackStateConfigEntry> definitions,
) {
  if (definitions.isEmpty) return null;
  final normalized = _canonicalConfigId(value);
  for (final definition in definitions) {
    if (definition.id == value ||
        _canonicalConfigId(definition.id) == normalized ||
        _canonicalConfigId(definition.name) == normalized ||
        definition.localizedLabels.values.any(
          (label) => _canonicalConfigId(label) == normalized,
        )) {
      return definition;
    }
  }
  return null;
}

String _resolvedConfigId(
  String? value, {
  required List<TrackStateConfigEntry> definitions,
}) {
  final text = (value ?? '').trim();
  if (text.isEmpty || text == 'null') return '';
  final match = _matchingConfigEntry(text, definitions);
  if (match != null) return match.id;
  return definitions.isEmpty ? _canonicalConfigId(text) : text;
}

String? _nullableResolvedId(
  Object? value, {
  required List<TrackStateConfigEntry> definitions,
}) {
  final text = value?.toString().trim();
  if (text == null || text.isEmpty || text == 'null') return null;
  return _resolvedConfigId(text, definitions: definitions);
}

String _statusIdForStatus(
  IssueStatus status, {
  required List<TrackStateConfigEntry> definitions,
  required TrackStateIssue currentIssue,
}) {
  if (currentIssue.status == status && currentIssue.statusId.isNotEmpty) {
    return currentIssue.statusId;
  }
  for (final definition in definitions) {
    if (_issueStatus(definition.id, definitions) == status) {
      return definition.id;
    }
  }
  return status.id;
}

String _canonicalConfigId(String? value) {
  final normalized = (value ?? '').trim().toLowerCase();
  if (normalized.isEmpty) return '';
  return normalized
      .replaceAll('&', 'and')
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-|-$'), '');
}

String _joinPath(String left, String right) {
  if (left.isEmpty) return right;
  return '$left/$right';
}

RepositoryIssueIndexEntry _repositoryIndexEntry(Map entry) {
  final childKeys = entry['children'];
  return RepositoryIssueIndexEntry(
    key: entry['key']?.toString() ?? '',
    path: entry['path']?.toString() ?? '',
    parentKey: _nullable(entry['parent']?.toString()),
    epicKey: _nullable(entry['epic']?.toString()),
    parentPath: _nullable(entry['parentPath']?.toString()),
    epicPath: _nullable(entry['epicPath']?.toString()),
    isArchived: entry['archived'] == true,
    childKeys: childKeys is List
        ? childKeys.map((value) => value.toString()).toList(growable: false)
        : const [],
  );
}

DeletedIssueTombstone _deletedIssueTombstone(
  Map entry, {
  required List<TrackStateConfigEntry> issueTypeDefinitions,
}) => DeletedIssueTombstone(
  key: entry['key']?.toString() ?? '',
  project: entry['project']?.toString() ?? '',
  formerPath: entry['formerPath']?.toString() ?? '',
  deletedAt: entry['deletedAt']?.toString() ?? '',
  summary: _nullable(entry['summary']?.toString()),
  issueTypeId: _nullableResolvedId(
    entry['issueType'],
    definitions: issueTypeDefinitions,
  ),
  parentKey: _nullable(entry['parent']?.toString()),
  epicKey: _nullable(entry['epic']?.toString()),
);

RepositoryIndex _deriveRepositoryIndex(
  List<TrackStateIssue> issues,
  List<DeletedIssueTombstone> deleted,
) {
  final pathByKey = {for (final issue in issues) issue.key: issue.storagePath};
  final childrenByKey = <String, List<String>>{};
  for (final issue in issues) {
    final relationshipParent = issue.parentKey ?? issue.epicKey;
    if (relationshipParent == null) continue;
    childrenByKey
        .putIfAbsent(relationshipParent, () => <String>[])
        .add(issue.key);
  }
  final entries = [
    for (final issue in issues)
      RepositoryIssueIndexEntry(
        key: issue.key,
        path: issue.storagePath,
        parentKey: issue.parentKey,
        epicKey: issue.epicKey,
        parentPath: issue.parentKey == null
            ? null
            : pathByKey[issue.parentKey!],
        epicPath: issue.epicKey == null ? null : pathByKey[issue.epicKey!],
        childKeys: [...(childrenByKey[issue.key] ?? const <String>[])]..sort(),
        isArchived: issue.isArchived,
      ),
  ]..sort((a, b) => a.key.compareTo(b.key));
  return RepositoryIndex(entries: entries, deleted: deleted);
}

RepositoryIndex _normalizeRepositoryIndex(
  RepositoryIndex index,
  List<TrackStateIssue> issues,
) {
  final issueByKey = {for (final issue in issues) issue.key: issue};
  final entriesByKey = {
    for (final entry in index.entries) entry.key: entry,
    for (final issue in issues)
      issue.key: RepositoryIssueIndexEntry(
        key: issue.key,
        path: issue.storagePath,
        parentKey: issue.parentKey,
        epicKey: issue.epicKey,
        childKeys: const [],
        isArchived: issue.isArchived,
      ),
  };
  final pathByKey = {
    for (final entry in entriesByKey.values) entry.key: entry.path,
  };
  final childrenByKey = <String, List<String>>{};
  for (final issue in issues) {
    final relationshipParent = issue.parentKey ?? issue.epicKey;
    if (relationshipParent == null) continue;
    childrenByKey
        .putIfAbsent(relationshipParent, () => <String>[])
        .add(issue.key);
  }

  final normalizedEntries = entriesByKey.values.map((entry) {
    final issue = issueByKey[entry.key];
    final childKeys = [...(childrenByKey[entry.key] ?? const <String>[])]
      ..sort();
    return entry.copyWith(
      parentPath: entry.parentKey == null ? null : pathByKey[entry.parentKey!],
      epicPath: entry.epicKey == null ? null : pathByKey[entry.epicKey!],
      childKeys: childKeys,
      isArchived: entry.isArchived || (issue?.isArchived ?? false),
    );
  }).toList()..sort((a, b) => a.key.compareTo(b.key));

  return RepositoryIndex(entries: normalizedEntries, deleted: index.deleted);
}

List<TrackStateIssue> _filterIssues(List<TrackStateIssue> issues, String jql) {
  final query = jql.trim().toLowerCase();
  if (query.isEmpty) return issues;

  Iterable<TrackStateIssue> results = issues;
  if (query.contains('status != done')) {
    results = results.where((issue) => issue.status != IssueStatus.done);
  }
  if (query.contains('status = done')) {
    results = results.where((issue) => issue.status == IssueStatus.done);
  }
  if (query.contains('issuetype = story') ||
      query.contains('issuetype = "story"')) {
    results = results.where((issue) => issue.issueType == IssueType.story);
  }
  final keyMatch = RegExp(
    r'(?:epic|parent)\s*=\s*([a-z]+-\d+)',
  ).firstMatch(query);
  if (keyMatch != null) {
    final key = keyMatch.group(1)!.toUpperCase();
    results = results.where(
      (issue) => issue.epicKey == key || issue.parentKey == key,
    );
  }
  final freeText = query
      .replaceAll(RegExp(r'project\s*=\s*[a-z]+'), '')
      .replaceAll(RegExp(r'status\s*(!=|=)\s*[a-z -]+'), '')
      .replaceAll(RegExp(r'issuetype\s*=\s*"?[a-z -]+"?'), '')
      .replaceAll(RegExp(r'(?:epic|parent)\s*=\s*[a-z]+-\d+'), '')
      .replaceAll(RegExp(r'order\s+by.+$'), '')
      .replaceAll(RegExp(r'\b(and|or)\b'), '')
      .trim();
  if (freeText.isNotEmpty && !freeText.contains('=')) {
    results = results.where(
      (issue) =>
          issue.summary.toLowerCase().contains(freeText) ||
          issue.key.toLowerCase().contains(freeText),
    );
  }
  final sorted = results.toList()
    ..sort(
      (a, b) => _priorityRank(b.priority).compareTo(_priorityRank(a.priority)),
    );
  return sorted;
}

String _mediaTypeForPath(String path) {
  final normalized = path.toLowerCase();
  if (normalized.endsWith('.svg')) return 'image/svg+xml';
  if (normalized.endsWith('.png')) return 'image/png';
  if (normalized.endsWith('.jpg') || normalized.endsWith('.jpeg')) {
    return 'image/jpeg';
  }
  if (normalized.endsWith('.json')) return 'application/json';
  if (normalized.endsWith('.md')) return 'text/markdown';
  if (normalized.endsWith('.txt')) return 'text/plain';
  return 'application/octet-stream';
}

int _priorityRank(IssuePriority priority) => switch (priority) {
  IssuePriority.highest => 4,
  IssuePriority.high => 3,
  IssuePriority.medium => 2,
  IssuePriority.low => 1,
};

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}

const _issueTypeDefinitions = [
  TrackStateConfigEntry(
    id: 'epic',
    name: 'Epic',
    localizedLabels: {'en': 'Epic'},
  ),
  TrackStateConfigEntry(
    id: 'story',
    name: 'Story',
    localizedLabels: {'en': 'Story'},
  ),
  TrackStateConfigEntry(
    id: 'task',
    name: 'Task',
    localizedLabels: {'en': 'Task'},
  ),
  TrackStateConfigEntry(
    id: 'subtask',
    name: 'Sub-task',
    localizedLabels: {'en': 'Sub-task'},
  ),
  TrackStateConfigEntry(id: 'bug', name: 'Bug', localizedLabels: {'en': 'Bug'}),
];

const _statusDefinitions = [
  TrackStateConfigEntry(
    id: 'todo',
    name: 'To Do',
    localizedLabels: {'en': 'To Do'},
  ),
  TrackStateConfigEntry(
    id: 'in-progress',
    name: 'In Progress',
    localizedLabels: {'en': 'In Progress'},
  ),
  TrackStateConfigEntry(
    id: 'in-review',
    name: 'In Review',
    localizedLabels: {'en': 'In Review'},
  ),
  TrackStateConfigEntry(
    id: 'done',
    name: 'Done',
    localizedLabels: {'en': 'Done'},
  ),
];

const _fieldDefinitions = [
  TrackStateFieldDefinition(
    id: 'summary',
    name: 'Summary',
    type: 'string',
    required: true,
    localizedLabels: {'en': 'Summary'},
  ),
  TrackStateFieldDefinition(
    id: 'description',
    name: 'Description',
    type: 'markdown',
    required: false,
    localizedLabels: {'en': 'Description'},
  ),
  TrackStateFieldDefinition(
    id: 'acceptanceCriteria',
    name: 'Acceptance Criteria',
    type: 'markdown',
    required: false,
    localizedLabels: {'en': 'Acceptance Criteria'},
  ),
  TrackStateFieldDefinition(
    id: 'priority',
    name: 'Priority',
    type: 'option',
    required: false,
    localizedLabels: {'en': 'Priority'},
  ),
  TrackStateFieldDefinition(
    id: 'assignee',
    name: 'Assignee',
    type: 'user',
    required: false,
    localizedLabels: {'en': 'Assignee'},
  ),
  TrackStateFieldDefinition(
    id: 'labels',
    name: 'Labels',
    type: 'array',
    required: false,
    localizedLabels: {'en': 'Labels'},
  ),
  TrackStateFieldDefinition(
    id: 'storyPoints',
    name: 'Story Points',
    type: 'number',
    required: false,
    localizedLabels: {'en': 'Story Points'},
  ),
];

const _priorityDefinitions = [
  TrackStateConfigEntry(
    id: 'highest',
    name: 'Highest',
    localizedLabels: {'en': 'Highest'},
  ),
  TrackStateConfigEntry(
    id: 'high',
    name: 'High',
    localizedLabels: {'en': 'High'},
  ),
  TrackStateConfigEntry(
    id: 'medium',
    name: 'Medium',
    localizedLabels: {'en': 'Medium'},
  ),
  TrackStateConfigEntry(id: 'low', name: 'Low', localizedLabels: {'en': 'Low'}),
];

const _versionDefinitions = [
  TrackStateConfigEntry(id: 'mvp', name: 'MVP', localizedLabels: {'en': 'MVP'}),
];

const _componentDefinitions = [
  TrackStateConfigEntry(
    id: 'tracker-core',
    name: 'Tracker Core',
    localizedLabels: {'en': 'Tracker Core'},
  ),
  TrackStateConfigEntry(
    id: 'flutter-ui',
    name: 'Flutter UI',
    localizedLabels: {'en': 'Flutter UI'},
  ),
  TrackStateConfigEntry(
    id: 'automation',
    name: 'Automation',
    localizedLabels: {'en': 'Automation'},
  ),
];

const _resolutionDefinitions = [
  TrackStateConfigEntry(
    id: 'done',
    name: 'Done',
    localizedLabels: {'en': 'Done'},
  ),
];

const _project = ProjectConfig(
  key: 'TRACK',
  name: 'TrackState.AI',
  repository: SetupTrackStateRepository.repositoryName,
  branch: SetupTrackStateRepository.sourceRef,
  defaultLocale: 'en',
  issueTypeDefinitions: _issueTypeDefinitions,
  statusDefinitions: _statusDefinitions,
  fieldDefinitions: _fieldDefinitions,
  priorityDefinitions: _priorityDefinitions,
  versionDefinitions: _versionDefinitions,
  componentDefinitions: _componentDefinitions,
  resolutionDefinitions: _resolutionDefinitions,
);

const _snapshot = TrackerSnapshot(
  project: _project,
  repositoryIndex: RepositoryIndex(
    entries: [
      RepositoryIssueIndexEntry(
        key: 'TRACK-1',
        path: 'TRACK/TRACK-1/main.md',
        childKeys: ['TRACK-12', 'TRACK-50'],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-12',
        path: 'TRACK/TRACK-1/TRACK-12/main.md',
        epicKey: 'TRACK-1',
        epicPath: 'TRACK/TRACK-1/main.md',
        childKeys: [],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-34',
        path: 'TRACK/TRACK-34/main.md',
        childKeys: ['TRACK-41'],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-41',
        path: 'TRACK/TRACK-34/TRACK-41/main.md',
        epicKey: 'TRACK-34',
        epicPath: 'TRACK/TRACK-34/main.md',
        childKeys: [],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-50',
        path: 'TRACK/TRACK-1/TRACK-50/main.md',
        epicKey: 'TRACK-1',
        epicPath: 'TRACK/TRACK-1/main.md',
        childKeys: [],
      ),
    ],
  ),
  issues: [
    TrackStateIssue(
      key: 'TRACK-1',
      project: 'TRACK',
      issueType: IssueType.epic,
      issueTypeId: 'epic',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Platform Foundation',
      description: 'Bootstrap the Git-native tracker.',
      assignee: 'ana',
      reporter: 'uladzimir',
      labels: ['mvp', 'git-native'],
      components: ['tracker-core'],
      fixVersionIds: ['mvp'],
      watchers: ['ana', 'uladzimir'],
      customFields: {'storyPoints': 13},
      parentKey: null,
      epicKey: null,
      parentPath: null,
      epicPath: null,
      progress: .62,
      updatedLabel: '2 minutes ago',
      acceptanceCriteria: ['Issue metadata follows canonical frontmatter.'],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      storagePath: 'TRACK/TRACK-1/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-12',
      project: 'TRACK',
      issueType: IssueType.story,
      issueTypeId: 'story',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'Implement Git sync service',
      description: 'Read and write tracker files through GitHub Contents API.',
      assignee: 'denis',
      reporter: 'ana',
      labels: ['sync'],
      components: ['tracker-core'],
      fixVersionIds: ['mvp'],
      watchers: ['ana', 'denis'],
      customFields: {
        'storyPoints': 8,
        'releaseTrain': ['web', 'mobile'],
      },
      parentKey: null,
      epicKey: 'TRACK-1',
      parentPath: null,
      epicPath: 'TRACK/TRACK-1/main.md',
      progress: .44,
      updatedLabel: '5 minutes ago',
      acceptanceCriteria: ['Push issue updates as commits.'],
      comments: [
        IssueComment(
          id: '0001',
          author: 'ana',
          body:
              'Use repository indexes for key lookup instead of full-tree scans.',
          updatedLabel: '2026-05-05T00:10:00Z',
          createdAt: '2026-05-05T00:10:00Z',
          storagePath: 'TRACK/TRACK-1/TRACK-12/comments/0001.md',
        ),
      ],
      links: [IssueLink(type: 'blocks', targetKey: 'TRACK-41')],
      attachments: [
        IssueAttachment(
          name: 'sync-sequence.svg',
          storagePath: 'TRACK/TRACK-1/TRACK-12/attachments/sync-sequence.svg',
          mediaType: 'image/svg+xml',
        ),
      ],
      isArchived: false,
      storagePath: 'TRACK/TRACK-1/TRACK-12/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-34',
      project: 'TRACK',
      issueType: IssueType.epic,
      issueTypeId: 'epic',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Mobile Experience',
      description: 'Deliver responsive layouts and touch optimized screens.',
      assignee: 'noah',
      reporter: 'ana',
      labels: ['mobile'],
      components: ['flutter-ui'],
      fixVersionIds: ['mvp'],
      watchers: ['ana', 'noah'],
      customFields: {'storyPoints': 5},
      parentKey: null,
      epicKey: null,
      parentPath: null,
      epicPath: null,
      progress: .52,
      updatedLabel: 'Jun 18',
      acceptanceCriteria: ['Layouts adapt without overflow.'],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      storagePath: 'TRACK/TRACK-34/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-41',
      project: 'TRACK',
      issueType: IssueType.story,
      issueTypeId: 'story',
      status: IssueStatus.todo,
      statusId: 'todo',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Polish mobile board interactions',
      description: 'Make drag and drop work on touch devices.',
      assignee: 'noah',
      reporter: 'ana',
      labels: ['mobile', 'board'],
      components: ['flutter-ui'],
      fixVersionIds: ['mvp'],
      watchers: ['noah'],
      customFields: {'storyPoints': 3},
      parentKey: null,
      epicKey: 'TRACK-34',
      parentPath: null,
      epicPath: 'TRACK/TRACK-34/main.md',
      progress: .12,
      updatedLabel: 'Jun 19',
      acceptanceCriteria: ['Cards can be moved between columns.'],
      comments: [],
      links: [IssueLink(type: 'is-blocked-by', targetKey: 'TRACK-12')],
      attachments: [],
      isArchived: false,
      storagePath: 'TRACK/TRACK-34/TRACK-41/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-50',
      project: 'TRACK',
      issueType: IssueType.task,
      issueTypeId: 'task',
      status: IssueStatus.done,
      statusId: 'done',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Create CI pipeline',
      description: 'Analyze, test, build, and deploy Pages artifacts.',
      assignee: 'priya',
      reporter: 'ana',
      labels: ['ci'],
      components: ['automation'],
      fixVersionIds: ['mvp'],
      watchers: ['priya'],
      customFields: {'storyPoints': 2},
      parentKey: null,
      epicKey: 'TRACK-1',
      parentPath: null,
      epicPath: 'TRACK/TRACK-1/main.md',
      progress: 1,
      updatedLabel: 'Jun 20',
      acceptanceCriteria: ['Workflow uploads web artifact.'],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      resolutionId: 'done',
      storagePath: 'TRACK/TRACK-1/TRACK-50/main.md',
    ),
  ],
);
