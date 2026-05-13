import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../domain/models/trackstate_models.dart';
import '../providers/github/github_trackstate_provider.dart';
import '../providers/trackstate_provider.dart';
import '../services/project_settings_validation_service.dart';
import '../services/jql_search_service.dart';

abstract interface class TrackStateRepository {
  bool get usesLocalPersistence;
  bool get supportsGitHubAuth;
  Future<TrackerSnapshot> loadSnapshot();
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  });
  Future<List<TrackStateIssue>> searchIssues(String jql);
  Future<RepositoryUser> connect(RepositoryConnection connection);
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue);
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue);
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  });
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  );
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  );
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body);
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  });
  Future<Uint8List> downloadAttachment(IssueAttachment attachment);
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue);
}

abstract interface class ProjectSettingsRepository {
  Future<TrackerSnapshot> saveProjectSettings(ProjectSettingsCatalog settings);
}

enum IssueHydrationScope { detail, comments, attachments }

extension TrackStateRepositoryAttachmentSupport on TrackStateRepository {
  String resolveIssueAttachmentPath(TrackStateIssue issue, String name) {
    final normalizedName = name.trim();
    if (normalizedName.isEmpty) {
      return _joinPath(
        _issueRoot(issue.storagePath),
        'attachments/attachment.bin',
      );
    }
    return _joinPath(
      _issueRoot(issue.storagePath),
      'attachments/${sanitizeAttachmentName(normalizedName)}',
    );
  }

  Future<bool> isIssueAttachmentLfsTracked(
    TrackStateIssue issue,
    String name,
  ) async {
    if (this case final ProviderBackedTrackStateRepository repository) {
      return repository.providerAdapter.isLfsTracked(
        resolveIssueAttachmentPath(issue, name),
      );
    }
    return false;
  }
}

class ProviderBackedTrackStateRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  static const RepositoryPermission _restrictedPermission =
      RepositoryPermission(
        canRead: false,
        canWrite: false,
        isAdmin: false,
        canCreateBranch: false,
        canManageAttachments: false,
        attachmentUploadMode: AttachmentUploadMode.none,
        supportsReleaseAttachmentWrites: false,
        canCheckCollaborators: false,
      );

  ProviderBackedTrackStateRepository({
    required TrackStateProviderAdapter provider,
    this.usesLocalPersistence = false,
    this.supportsGitHubAuth = true,
    http.Client? githubClient,
    JqlSearchService searchService = const JqlSearchService(),
  }) : _provider = provider,
       _githubClient = githubClient,
       _searchService = searchService,
       _session = ProviderSession(
         providerType: provider.providerType,
         connectionState: ProviderConnectionState.disconnected,
         resolvedUserIdentity: provider.repositoryLabel,
         canRead: _restrictedPermission.canRead,
         canWrite: _restrictedPermission.canWrite,
         canCreateBranch: _restrictedPermission.canCreateBranch,
         canManageAttachments: _restrictedPermission.canManageAttachments,
         attachmentUploadMode: _restrictedPermission.attachmentUploadMode,
         supportsReleaseAttachmentWrites:
             _restrictedPermission.supportsReleaseAttachmentWrites,
         canCheckCollaborators: _restrictedPermission.canCheckCollaborators,
       );

  final TrackStateProviderAdapter _provider;
  final http.Client? _githubClient;
  final JqlSearchService _searchService;
  final ProjectSettingsValidationService _projectSettingsValidationService =
      const ProjectSettingsValidationService();
  @override
  final bool usesLocalPersistence;
  @override
  final bool supportsGitHubAuth;
  TrackerSnapshot? _snapshot;
  final Set<String> _knownTombstoneKeys = <String>{};
  final Map<String, DeletedIssueTombstone> _knownTombstonesByKey =
      <String, DeletedIssueTombstone>{};
  final Map<String, String?> _snapshotArtifactRevisions = <String, String?>{};
  List<RepositoryTreeEntry> _snapshotTree = const <RepositoryTreeEntry>[];
  Set<String> _snapshotBlobPaths = const <String>{};
  final ProviderSession _session;
  final Queue<Completer<void>> _pendingDeleteMutations =
      Queue<Completer<void>>();
  bool _deleteMutationInProgress = false;
  TrackerStartupRecovery? _startupRecovery;

  TrackStateProviderAdapter get providerAdapter => _provider;
  ProviderSession? get session => _session;
  TrackerSnapshot? get cachedSnapshot => _snapshot;

  void replaceCachedState({
    TrackerSnapshot? snapshot,
    List<RepositoryTreeEntry>? tree,
  }) {
    final previousSnapshot = _snapshot;
    final nextSnapshot = snapshot ?? previousSnapshot;
    if (snapshot != null) {
      _snapshot = snapshot;
    }
    if (tree != null) {
      _snapshotTree = tree;
      _snapshotBlobPaths = tree
          .where((entry) => entry.type == 'blob')
          .map((entry) => entry.path)
          .toSet();
      _rebuildCachedArtifactRevisions(
        previousSnapshot: previousSnapshot,
        nextSnapshot: nextSnapshot,
        blobPaths: _snapshotBlobPaths,
      );
    }
  }

  Future<void> _acquireDeleteMutationLock() async {
    if (!_deleteMutationInProgress) {
      _deleteMutationInProgress = true;
      return;
    }
    final waiter = Completer<void>();
    _pendingDeleteMutations.addLast(waiter);
    await waiter.future;
  }

  void _releaseDeleteMutationLock() {
    if (_pendingDeleteMutations.isEmpty) {
      _deleteMutationInProgress = false;
      return;
    }
    _pendingDeleteMutations.removeFirst().complete();
  }

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    RepositoryPermission initialPermission = _restrictedPermission;
    try {
      initialPermission = await _provider.getPermission();
    } catch (_) {
      initialPermission = _restrictedPermission;
    }
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
        connectionState: ProviderConnectionState.error,
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
    _startupRecovery = null;
    _snapshotArtifactRevisions.clear();
    final snapshot = await _loadSetupSnapshot();
    _snapshot = snapshot;
    return snapshot;
  }

  Future<TrackStateIssue> hydrateIssue(
    TrackStateIssue issue, {
    Set<IssueHydrationScope> scopes = const {IssueHydrationScope.detail},
    bool force = false,
  }) async {
    if (usesLocalPersistence && !force) {
      final snapshot = _snapshot ?? await loadSnapshot();
      return snapshot.issues.firstWhere(
        (candidate) => candidate.key == issue.key,
        orElse: () => issue,
      );
    }
    final currentSnapshot = _snapshot ?? await loadSnapshot();
    final currentIssue = force
        ? issue
        : currentSnapshot.issues.firstWhere(
            (candidate) => candidate.key == issue.key,
            orElse: () => issue,
          );
    if (!force && _hasHydratedScopes(currentIssue, scopes)) {
      return currentIssue;
    }
    if (currentIssue.storagePath.isEmpty) {
      throw TrackStateRepositoryException(
        'Issue ${currentIssue.key} cannot be hydrated because it has no repository file path.',
      );
    }

    if (_snapshotTree.isEmpty || _snapshotBlobPaths.isEmpty) {
      final tree = await _provider.listTree(ref: _provider.dataRef);
      _snapshotTree = tree;
      _snapshotBlobPaths = tree
          .where((entry) => entry.type == 'blob')
          .map((entry) => entry.path)
          .toSet();
    }

    final issueRoot = _issueRoot(currentIssue.storagePath);
    final shouldLoadDetail =
        scopes.contains(IssueHydrationScope.detail) ||
        currentIssue.hasDetailLoaded;
    final shouldLoadComments =
        scopes.contains(IssueHydrationScope.comments) ||
        currentIssue.hasCommentsLoaded;
    final shouldLoadAttachments =
        scopes.contains(IssueHydrationScope.attachments) ||
        currentIssue.hasAttachmentsLoaded;

    final markdown = !force && currentIssue.rawMarkdown.isNotEmpty
        ? currentIssue.rawMarkdown
        : await _getRepositoryText(currentIssue.storagePath);
    final acceptanceMarkdown = shouldLoadDetail
        ? await _tryReadIssueAcceptance(issueRoot)
        : _acceptanceCriteriaMarkdown(currentIssue.acceptanceCriteria);
    final comments = shouldLoadComments
        ? await _loadComments(
            blobPaths: _snapshotBlobPaths,
            issueRoot: issueRoot,
          )
        : currentIssue.comments;
    final links = shouldLoadDetail
        ? await _loadLinks(blobPaths: _snapshotBlobPaths, issueRoot: issueRoot)
        : currentIssue.links;
    final attachments = shouldLoadAttachments
        ? await _loadAttachments(tree: _snapshotTree, issueRoot: issueRoot)
        : currentIssue.attachments;
    final hydratedIssue =
        _parseIssue(
          storagePath: currentIssue.storagePath,
          markdown: markdown,
          acceptanceMarkdown: acceptanceMarkdown,
          comments: comments,
          links: links,
          attachments: attachments,
          repositoryIndexEntry: currentSnapshot.repositoryIndex.entryForKey(
            currentIssue.key,
          ),
          issueTypeDefinitions: currentSnapshot.project.issueTypeDefinitions,
          statusDefinitions: currentSnapshot.project.statusDefinitions,
          priorityDefinitions: currentSnapshot.project.priorityDefinitions,
          resolutionDefinitions: currentSnapshot.project.resolutionDefinitions,
        ).copyWith(
          hasDetailLoaded: shouldLoadDetail,
          hasCommentsLoaded: shouldLoadComments,
          hasAttachmentsLoaded: shouldLoadAttachments,
        );
    _replaceIssueInSnapshot(hydratedIssue);
    return hydratedIssue;
  }

  @override
  Future<TrackerSnapshot> saveProjectSettings(
    ProjectSettingsCatalog settings,
  ) async {
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }
    final normalizedSettings = _projectSettingsValidationService
        .normalizeForPersistence(settings);
    _projectSettingsValidationService.validate(normalizedSettings);
    await _provider.ensureCleanWorktree();

    final writeBranch = await _provider.resolveWriteBranch();
    final blobPaths = (await _provider.listTree(ref: writeBranch))
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
        jsonDecode(
              (await _provider.readTextFile(
                projectPath,
                ref: writeBranch,
              )).content,
            )
            as Map<String, Object?>;
    final configRoot = _resolveConfigRoot(projectJson, dataRoot);
    final persistedSettings = normalizedSettings.copyWith(
      fieldDefinitions: _persistedFieldDefinitions(
        normalizedSettings.fieldDefinitions,
        persistedFieldIds: await _persistedFieldIds(
          path: _joinPath(configRoot, 'fields.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
    );
    final existingSupportedLocales = _resolveSupportedLocales(
      projectJson: projectJson,
      blobPaths: blobPaths,
      configRoot: configRoot,
      defaultLocale: projectJson['defaultLocale']?.toString() ?? 'en',
    );
    final changes = <RepositoryFileChange>[
      RepositoryTextFileChange(
        path: projectPath,
        content:
            '${jsonEncode(_settingsProjectJson(projectJson, persistedSettings))}\n',
        expectedRevision: await _existingRevision(
          path: projectPath,
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'statuses.json'),
        content:
            '${jsonEncode(_settingsStatusesJson(persistedSettings.statusDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'statuses.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'issue-types.json'),
        content:
            '${jsonEncode(_settingsIssueTypesJson(persistedSettings.issueTypeDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'issue-types.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'fields.json'),
        content:
            '${jsonEncode(_settingsFieldsJson(persistedSettings.fieldDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'fields.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'workflows.json'),
        content:
            '${jsonEncode(_settingsWorkflowsJson(persistedSettings.workflowDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'workflows.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'priorities.json'),
        content:
            '${jsonEncode(_settingsConfigEntriesJson(persistedSettings.priorityDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'priorities.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'versions.json'),
        content:
            '${jsonEncode(_settingsConfigEntriesJson(persistedSettings.versionDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'versions.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'components.json'),
        content:
            '${jsonEncode(_settingsConfigEntriesJson(persistedSettings.componentDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'components.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
      RepositoryTextFileChange(
        path: _joinPath(configRoot, 'resolutions.json'),
        content:
            '${jsonEncode(_settingsConfigEntriesJson(persistedSettings.resolutionDefinitions))}\n',
        expectedRevision: await _existingRevision(
          path: _joinPath(configRoot, 'resolutions.json'),
          ref: writeBranch,
          blobPaths: blobPaths,
        ),
      ),
    ];
    for (final locale in normalizedSettings.effectiveSupportedLocales) {
      final path = _joinPath(configRoot, 'i18n/$locale.json');
      changes.add(
        RepositoryTextFileChange(
          path: path,
          content:
              '${jsonEncode(_localizedLabelsJson(persistedSettings, locale))}\n',
          expectedRevision: await _existingRevision(
            path: path,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      );
    }
    for (final locale in existingSupportedLocales) {
      if (normalizedSettings.effectiveSupportedLocales.contains(locale)) {
        continue;
      }
      final path = _joinPath(configRoot, 'i18n/$locale.json');
      if (!blobPaths.contains(path)) {
        continue;
      }
      changes.add(
        RepositoryDeleteFileChange(
          path: path,
          expectedRevision: await _existingRevision(
            path: path,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      );
    }
    final mutator = _provider as RepositoryFileMutator?;
    if (mutator == null) {
      for (final change in changes) {
        switch (change) {
          case RepositoryTextFileChange():
            await _provider.writeTextFile(
              RepositoryWriteRequest(
                path: change.path,
                content: change.content,
                message: 'Update project settings',
                branch: writeBranch,
                expectedRevision: change.expectedRevision,
              ),
            );
          case RepositoryDeleteFileChange():
            throw const TrackStateRepositoryException(
              'This repository implementation does not support deleting locale configuration files.',
            );
          case RepositoryBinaryFileChange():
            throw const TrackStateRepositoryException(
              'Project settings do not support binary file changes.',
            );
        }
      }
    } else {
      await mutator.applyFileChanges(
        RepositoryFileChangeRequest(
          branch: writeBranch,
          message: 'Update project settings',
          changes: changes,
        ),
      );
    }
    return loadSnapshot();
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    var snapshot = _snapshot ?? await loadSnapshot();
    if (!usesLocalPersistence &&
        _searchService.requiresIssueDetails(jql) &&
        snapshot.readiness.domainState(TrackerDataDomain.issueDetails) !=
            TrackerLoadState.ready) {
      for (final issue in snapshot.issues) {
        await hydrateIssue(issue, scopes: const {IssueHydrationScope.detail});
      }
      snapshot = _snapshot ?? snapshot;
    }
    return _searchService.search(
      issues: snapshot.issues,
      project: snapshot.project,
      jql: jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async {
    final page = await searchIssuePage(jql, maxResults: 2147483647);
    return page.issues;
  }

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    final normalizedSummary = summary.trim();
    if (normalizedSummary.isEmpty) {
      throw const TrackStateRepositoryException(
        'Issue summary is required before creating an issue.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final snapshot = _snapshot ?? await loadSnapshot();
    await _provider.ensureCleanWorktree();

    final project = snapshot.project;
    final key = _nextIssueKey(snapshot);
    final writeBranch = await _provider.resolveWriteBranch();
    final issuePath = _nextIssuePath(snapshot, key);
    final createdAt = DateTime.now().toUtc().toIso8601String();
    final issueTypeId = _defaultIssueTypeId(project);
    final statusId = _defaultStatusId(project);
    final priorityId = _defaultPriorityId(project);
    final author = _defaultAuthor(_session.resolvedUserIdentity);
    final markdown = _buildIssueMarkdown(
      key: key,
      projectKey: project.key,
      summary: normalizedSummary,
      description: description.trim(),
      customFields: customFields,
      issueTypeId: issueTypeId,
      statusId: statusId,
      priorityId: priorityId,
      assignee: author,
      reporter: author,
      createdAt: createdAt,
    );

    await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: issuePath,
        content: markdown,
        message: 'Create $key',
        branch: writeBranch,
      ),
    );

    final refreshed = await loadSnapshot();
    return refreshed.issues.firstWhere(
      (issue) => issue.key == key,
      orElse: () => _parseIssue(
        storagePath: issuePath,
        markdown: markdown,
        comments: const [],
        links: const [],
        attachments: const [],
        repositoryIndexEntry: RepositoryIssueIndexEntry(
          key: key,
          path: issuePath,
          childKeys: const [],
        ),
        issueTypeDefinitions: project.issueTypeDefinitions,
        statusDefinitions: project.statusDefinitions,
        priorityDefinitions: project.priorityDefinitions,
        resolutionDefinitions: project.resolutionDefinitions,
      ),
    );
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
    final snapshot = _snapshot ?? await loadSnapshot();
    final currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    final writeBranch = await _provider.resolveWriteBranch();
    final blobPaths = (await _provider.listTree(ref: writeBranch))
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    if (!blobPaths.contains(currentIssue.storagePath)) {
      throw TrackStateRepositoryException(
        'Could not find repository artifacts for ${currentIssue.key}.',
      );
    }
    final file = await _provider.readTextFile(
      currentIssue.storagePath,
      ref: writeBranch,
    );
    final updatedMarkdown = _replaceSection(
      file.content,
      'Description',
      normalizedDescription,
    );
    await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: currentIssue.storagePath,
        content: updatedMarkdown,
        message: 'Update ${currentIssue.key} description',
        branch: writeBranch,
        expectedRevision: file.revision,
      ),
    );

    final updatedIssue = currentIssue.copyWith(
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

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot receive comments.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }

    final persistedBody = body.trimRight();
    if (persistedBody.trim().isEmpty) {
      throw const TrackStateRepositoryException(
        'Comment body is required before saving.',
      );
    }

    final snapshot = _snapshot ?? await loadSnapshot();
    final currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    final writeBranch = await _provider.resolveWriteBranch();
    final blobPaths = (await _provider.listTree(ref: writeBranch))
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    final issueRoot = _issueRoot(currentIssue.storagePath);
    final nextCommentId = _nextCommentId(
      blobPaths: blobPaths,
      issueRoot: issueRoot,
    );
    final commentPath = _joinPath(issueRoot, 'comments/$nextCommentId.md');
    final timestamp = DateTime.now().toUtc().toIso8601String();
    final author = _defaultAuthor(_session.resolvedUserIdentity);
    final markdown = _buildCommentMarkdown(
      author: author,
      createdAt: timestamp,
      body: persistedBody,
    );
    final result = await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: commentPath,
        content: markdown,
        message: 'Add comment to ${currentIssue.key}',
        branch: writeBranch,
      ),
    );

    final updatedIssue = currentIssue.copyWith(
      hasCommentsLoaded: true,
      comments: [
        ...currentIssue.comments,
        IssueComment(
          id: nextCommentId,
          author: author,
          body: persistedBody,
          updatedLabel: timestamp,
          createdAt: timestamp,
          updatedAt: timestamp,
          storagePath: commentPath,
        ),
      ]..sort((left, right) => left.id.compareTo(right.id)),
    );
    _snapshotArtifactRevisions[commentPath] = result.revision;
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot receive attachments.',
      );
    }
    final snapshot = _snapshot ?? await loadSnapshot();
    final permission = await _provider.getPermission();
    final attachmentStorage = snapshot.project.attachmentStorage;
    if (attachmentStorage.mode == AttachmentStorageMode.githubReleases) {
      final githubReleases = attachmentStorage.githubReleases;
      if (githubReleases == null || githubReleases.tagPrefix.trim().isEmpty) {
        throw const TrackStateRepositoryException(
          'GitHub Releases attachment storage requires a non-empty tag prefix.',
        );
      }
      if (!permission.supportsReleaseAttachmentWrites) {
        throw TrackStateRepositoryException(
          permission.releaseAttachmentWriteFailureReason?.trim().isNotEmpty ==
                  true
              ? permission.releaseAttachmentWriteFailureReason!.trim()
              : 'GitHub Releases attachment storage requires GitHub '
                    'authentication/configuration that supports release '
                    'uploads. This repository session cannot upload '
                    'release-backed attachments.',
        );
      }
    } else if (!permission.canManageAttachments) {
      throw const TrackStateRepositoryException(
        'This repository session does not allow attachment uploads.',
      );
    }
    final normalizedName = name.trim();
    if (normalizedName.isEmpty) {
      throw const TrackStateRepositoryException(
        'Attachment name is required before uploading.',
      );
    }
    if (bytes.isEmpty) {
      throw const TrackStateRepositoryException(
        'Attachment bytes are required before uploading.',
      );
    }

    var currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    if (!currentIssue.hasAttachmentsLoaded) {
      currentIssue = await hydrateIssue(
        currentIssue,
        scopes: const {IssueHydrationScope.attachments},
      );
    }
    if (attachmentStorage.mode == AttachmentStorageMode.githubReleases) {
      final githubReleases = attachmentStorage.githubReleases!;
      final releaseStore = switch (_provider) {
        final RepositoryReleaseAttachmentStore supported => supported,
        _ => throw const TrackStateRepositoryException(
          'This repository provider does not support GitHub Releases '
          'attachment uploads.',
        ),
      };
      final writeBranch = await _provider.resolveWriteBranch();
      final attachmentPath = resolveIssueAttachmentPath(
        currentIssue,
        normalizedName,
      );
      final attachmentMetadataPath = _attachmentMetadataPath(
        _issueRoot(currentIssue.storagePath),
      );
      final metadataRevision = await _existingRevision(
        path: attachmentMetadataPath,
        ref: writeBranch,
        blobPaths: _snapshotBlobPaths,
      );
      final timestamp = DateTime.now().toUtc().toIso8601String();
      final author = _defaultAuthor(_session.resolvedUserIdentity);
      final releaseTag = githubReleases.releaseTagForIssue(currentIssue.key);
      final assetName = sanitizeAttachmentName(normalizedName);
      final releaseAssetNames = {
        for (final attachment in currentIssue.attachments)
          if (attachment.storageBackend ==
                  AttachmentStorageMode.githubReleases &&
              attachment.githubReleaseTag == releaseTag)
            attachment.githubReleaseAssetName ?? attachment.name,
      };
      final previousReleaseAttachment = currentIssue.attachments
          .where(
            (attachment) =>
                attachment.storagePath == attachmentPath &&
                attachment.storageBackend ==
                    AttachmentStorageMode.githubReleases &&
                attachment.githubReleaseTag == releaseTag,
          )
          .firstOrNull;
      final rollbackAttachment = previousReleaseAttachment == null
          ? null
          : await releaseStore.readReleaseAttachment(
              RepositoryReleaseAttachmentReadRequest(
                releaseTag: previousReleaseAttachment.githubReleaseTag!,
                assetName:
                    previousReleaseAttachment.githubReleaseAssetName ??
                    previousReleaseAttachment.name,
                assetId: previousReleaseAttachment.revisionOrOid,
              ),
            );
      final releaseWriteResult = await releaseStore.writeReleaseAttachment(
        RepositoryReleaseAttachmentWriteRequest(
          issueKey: currentIssue.key,
          releaseTag: releaseTag,
          releaseTitle: githubReleases.releaseTitleForIssue(currentIssue.key),
          assetName: assetName,
          bytes: bytes,
          mediaType: _mediaTypeForPath(assetName),
          branch: writeBranch,
          allowedAssetNames: releaseAssetNames,
        ),
      );
      final updatedAttachment = IssueAttachment(
        id: attachmentPath,
        name: normalizedName,
        mediaType: _mediaTypeForPath(normalizedName),
        sizeBytes: bytes.length,
        author: author,
        createdAt: timestamp,
        storagePath: attachmentPath,
        revisionOrOid: releaseWriteResult.assetId,
        storageBackend: AttachmentStorageMode.githubReleases,
        githubReleaseTag: releaseWriteResult.releaseTag,
        githubReleaseAssetName: releaseWriteResult.assetName,
      );
      final updatedAttachments = [
        for (final candidate in currentIssue.attachments)
          if (candidate.storagePath == attachmentPath)
            updatedAttachment
          else
            candidate,
        if (!currentIssue.attachments.any(
          (candidate) => candidate.storagePath == attachmentPath,
        ))
          updatedAttachment,
      ]..sort(_sortAttachmentsNewestFirst);
      final metadataWriteResult = await () async {
        try {
          return await _provider.writeTextFile(
            RepositoryWriteRequest(
              path: attachmentMetadataPath,
              content:
                  '${jsonEncode(_attachmentMetadataJson(updatedAttachments))}\n',
              message: 'Update attachment metadata for ${currentIssue.key}',
              branch: writeBranch,
              expectedRevision: metadataRevision,
            ),
          );
        } catch (error, stackTrace) {
          try {
            await releaseStore.deleteReleaseAttachment(
              RepositoryReleaseAttachmentDeleteRequest(
                releaseTag: releaseWriteResult.releaseTag,
                assetId: releaseWriteResult.assetId,
                assetName: releaseWriteResult.assetName,
              ),
            );
            if (previousReleaseAttachment != null &&
                rollbackAttachment != null) {
              await releaseStore.writeReleaseAttachment(
                RepositoryReleaseAttachmentWriteRequest(
                  issueKey: currentIssue.key,
                  releaseTag: previousReleaseAttachment.githubReleaseTag!,
                  releaseTitle: githubReleases.releaseTitleForIssue(
                    currentIssue.key,
                  ),
                  assetName:
                      previousReleaseAttachment.githubReleaseAssetName ??
                      previousReleaseAttachment.name,
                  bytes: rollbackAttachment.bytes,
                  mediaType: previousReleaseAttachment.mediaType,
                  branch: writeBranch,
                  allowedAssetNames: releaseAssetNames,
                ),
              );
            }
          } catch (rollbackError) {
            throw TrackStateRepositoryException(
              'Could not update attachment metadata for ${currentIssue.key} '
              'after uploading GitHub release asset $assetName. '
              'Rollback also failed: $rollbackError',
            );
          }
          Error.throwWithStackTrace(error, stackTrace);
        }
      }();
      _snapshotArtifactRevisions[attachmentMetadataPath] =
          metadataWriteResult.revision;
      _snapshotBlobPaths = {..._snapshotBlobPaths, attachmentMetadataPath};
      final updatedIssue = currentIssue.copyWith(
        hasAttachmentsLoaded: true,
        attachments: updatedAttachments,
      );
      _replaceCachedIssue(updatedIssue);
      return updatedIssue;
    }
    final writeBranch = await _provider.resolveWriteBranch();
    final attachmentPath = resolveIssueAttachmentPath(
      currentIssue,
      normalizedName,
    );
    final attachmentMetadataPath = _attachmentMetadataPath(
      _issueRoot(currentIssue.storagePath),
    );
    final existingRevision = _snapshotArtifactRevisions[attachmentPath];
    final metadataRevision = await _existingRevision(
      path: attachmentMetadataPath,
      ref: writeBranch,
      blobPaths: _snapshotBlobPaths,
    );
    final lfsTracked = await _provider.isLfsTracked(attachmentPath);
    if (lfsTracked &&
        permission.attachmentUploadMode == AttachmentUploadMode.noLfs) {
      throw const TrackStateRepositoryException(
        'This repository session is download-only for Git LFS attachments.',
      );
    }

    final timestamp = DateTime.now().toUtc().toIso8601String();
    final author = _defaultAuthor(_session.resolvedUserIdentity);
    final attachmentWriteResult = await _provider.writeAttachment(
      RepositoryAttachmentWriteRequest(
        path: attachmentPath,
        bytes: bytes,
        message: 'Upload attachment to ${currentIssue.key}',
        branch: writeBranch,
        expectedRevision: existingRevision,
      ),
    );
    _snapshotArtifactRevisions[attachmentPath] = attachmentWriteResult.revision;
    final persistedAttachmentArtifact = await _provider.readAttachment(
      attachmentPath,
      ref: writeBranch,
    );
    final updatedAttachment = IssueAttachment(
      id: attachmentPath,
      name: attachmentPath.split('/').last,
      mediaType: _mediaTypeForPath(attachmentPath),
      sizeBytes: bytes.length,
      author: author,
      createdAt: timestamp,
      storagePath: attachmentPath,
      revisionOrOid: _attachmentRevisionOrOid(
        attachment: persistedAttachmentArtifact,
        isLfsTracked: lfsTracked,
      ),
      storageBackend: AttachmentStorageMode.repositoryPath,
      repositoryPath: attachmentPath,
    );
    final updatedAttachments = [
      for (final candidate in currentIssue.attachments)
        if (candidate.storagePath == attachmentPath)
          updatedAttachment
        else
          candidate,
      if (!currentIssue.attachments.any(
        (candidate) => candidate.storagePath == attachmentPath,
      ))
        updatedAttachment,
    ]..sort(_sortAttachmentsNewestFirst);
    final metadataWriteResult = await _provider.writeTextFile(
      RepositoryWriteRequest(
        path: attachmentMetadataPath,
        content: '${jsonEncode(_attachmentMetadataJson(updatedAttachments))}\n',
        message: 'Update attachment metadata for ${currentIssue.key}',
        branch: writeBranch,
        expectedRevision: metadataRevision,
      ),
    );
    _snapshotArtifactRevisions[attachmentMetadataPath] =
        metadataWriteResult.revision;
    _snapshotBlobPaths = {
      ..._snapshotBlobPaths,
      attachmentPath,
      attachmentMetadataPath,
    };
    final updatedIssue = currentIssue.copyWith(
      hasAttachmentsLoaded: true,
      attachments: updatedAttachments,
    );
    _replaceCachedIssue(updatedIssue);
    return updatedIssue;
  }

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async {
    if (attachment.storageBackend == AttachmentStorageMode.githubReleases) {
      final releaseTag = attachment.githubReleaseTag?.trim() ?? '';
      final assetName = attachment.githubReleaseAssetName?.trim() ?? '';
      if (releaseTag.isEmpty || assetName.isEmpty) {
        throw TrackStateRepositoryException(
          'GitHub Releases attachment metadata is incomplete for '
          '${attachment.name}.',
        );
      }
      final request = RepositoryReleaseAttachmentReadRequest(
        releaseTag: releaseTag,
        assetName: assetName,
        assetId: attachment.revisionOrOid,
      );
      final artifact = switch (_provider) {
        final RepositoryReleaseAttachmentStore supported =>
          await supported.readReleaseAttachment(request),
        final RepositoryGitHubIdentityResolver identityResolver =>
          await () async {
            final failureReason = await identityResolver
                .releaseAttachmentIdentityFailureReason();
            if (failureReason?.trim().isNotEmpty == true) {
              throw TrackStateRepositoryException(failureReason!.trim());
            }
            final repository = await identityResolver
                .resolveGitHubRepositoryIdentity();
            if (repository == null || repository.trim().isEmpty) {
              final reason = await identityResolver
                  .releaseAttachmentIdentityFailureReason();
              throw TrackStateRepositoryException(
                reason?.trim().isNotEmpty == true
                    ? reason!.trim()
                    : 'This repository provider does not support GitHub Releases '
                          'attachment downloads.',
              );
            }
            return GitHubTrackStateProvider(
              client: _githubClient,
              repositoryName: repository,
            ).readReleaseAttachmentForRepository(
              repository: repository,
              request: request,
            );
          }(),
        _ => throw const TrackStateRepositoryException(
          'This repository provider does not support GitHub Releases '
          'attachment downloads.',
        ),
      };
      return artifact.bytes;
    }
    final artifact = await _provider.readAttachment(
      attachment.resolvedRepositoryPath,
      ref: _provider.dataRef,
    );
    return artifact.bytes;
  }

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async {
    final historyReader = switch (_provider) {
      final RepositoryHistoryReader supported => supported,
      _ => null,
    };
    if (historyReader == null) {
      return const <IssueHistoryEntry>[];
    }
    final issueRoot = _issueRoot(issue.storagePath);
    final commits = await historyReader.listHistory(
      ref: _provider.dataRef,
      path: issueRoot,
    );
    return _normalizeIssueHistory(issue: issue, commits: commits);
  }

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async {
    if (issue.storagePath.isEmpty) {
      throw const TrackStateRepositoryException(
        'This issue has no repository file path and cannot be archived.',
      );
    }
    final permission = await _provider.getPermission();
    if (!permission.canWrite) {
      throw const TrackStateRepositoryException(
        'Connect a repository session with write access first.',
      );
    }
    final mutator = switch (_provider) {
      final RepositoryFileMutator supported => supported,
      _ => throw const TrackStateRepositoryException(
        'This repository provider does not support archiving issues yet.',
      ),
    };
    final snapshot = _snapshot ?? await loadSnapshot();
    final currentIssue = snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );

    try {
      final writeBranch = await _provider.resolveWriteBranch();
      final tree = await _provider.listTree(ref: writeBranch);
      final blobPaths = tree
          .where((entry) => entry.type == 'blob')
          .map((entry) => entry.path)
          .toSet();
      final projectRoot = currentIssue.storagePath.split('/').first;
      if (projectRoot.isEmpty) {
        throw const TrackStateRepositoryException(
          'Could not resolve the project root for the issue being archived.',
        );
      }
      final issueArtifactPaths = _issueArtifactPaths(
        blobPaths,
        currentIssue.storagePath,
      );
      if (!issueArtifactPaths.contains(currentIssue.storagePath)) {
        throw TrackStateRepositoryException(
          'Could not find repository artifacts for ${currentIssue.key}.',
        );
      }
      final issueRoot = _issueRoot(currentIssue.storagePath);
      final archivedStoragePath = _archivedIssueStoragePath(
        projectRoot,
        currentIssue.key,
      );
      final archivedIssueRoot = _issueRoot(archivedStoragePath);

      final issueFile = await _provider.readTextFile(
        currentIssue.storagePath,
        ref: writeBranch,
      );
      final updatedMarkdown = _replaceFrontmatterValue(
        issueFile.content,
        'archived',
        'true',
      );
      final updatedIssues = [
        for (final candidate in snapshot.issues)
          if (candidate.key == currentIssue.key)
            candidate.copyWith(
              rawMarkdown: updatedMarkdown,
              updatedLabel: 'just now',
              isArchived: true,
              storagePath: archivedStoragePath,
            )
          else
            candidate,
      ]..sort((a, b) => a.key.compareTo(b.key));
      final repositoryIndex = _deriveRepositoryIndex(
        updatedIssues,
        snapshot.repositoryIndex.deleted,
      );
      final issuesIndexPath = _joinPath(
        projectRoot,
        '.trackstate/index/issues.json',
      );
      final changes = <RepositoryFileChange>[];
      for (final artifactPath in issueArtifactPaths) {
        final targetPath = artifactPath == currentIssue.storagePath
            ? archivedStoragePath
            : _joinPath(
                archivedIssueRoot,
                artifactPath.substring(issueRoot.length + 1),
              );
        if (artifactPath == currentIssue.storagePath) {
          changes.add(
            RepositoryTextFileChange(
              path: targetPath,
              content: updatedMarkdown,
              expectedRevision: artifactPath == targetPath
                  ? issueFile.revision
                  : await _existingArtifactRevision(
                      path: targetPath,
                      ref: writeBranch,
                      blobPaths: blobPaths,
                    ),
            ),
          );
          if (artifactPath != targetPath) {
            changes.add(
              RepositoryDeleteFileChange(
                path: artifactPath,
                expectedRevision: issueFile.revision,
              ),
            );
          }
          continue;
        }

        final artifact = await _provider.readAttachment(
          artifactPath,
          ref: writeBranch,
        );
        changes.add(
          RepositoryBinaryFileChange(
            path: targetPath,
            bytes: artifact.bytes,
            expectedRevision: artifactPath == targetPath
                ? artifact.revision
                : await _existingArtifactRevision(
                    path: targetPath,
                    ref: writeBranch,
                    blobPaths: blobPaths,
                  ),
          ),
        );
        if (artifactPath != targetPath) {
          changes.add(
            RepositoryDeleteFileChange(
              path: artifactPath,
              expectedRevision: artifact.revision,
            ),
          );
        }
      }
      changes.add(
        RepositoryTextFileChange(
          path: issuesIndexPath,
          content:
              '${jsonEncode(_repositoryIndexEntriesJson(repositoryIndex.entries))}\n',
          expectedRevision: await _existingRevision(
            path: issuesIndexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      );

      await mutator.applyFileChanges(
        RepositoryFileChangeRequest(
          branch: writeBranch,
          message: 'Archive ${currentIssue.key}',
          changes: changes,
        ),
      );

      final indexedUpdatedIssues = [
        for (final updatedIssue in updatedIssues)
          updatedIssue.withRepositoryIndex(
            repositoryIndex.entryForKey(updatedIssue.key),
          ),
      ]..sort((a, b) => a.key.compareTo(b.key));
      _snapshot = TrackerSnapshot(
        project: snapshot.project,
        repositoryIndex: repositoryIndex,
        issues: indexedUpdatedIssues,
      );
      return indexedUpdatedIssues.singleWhere(
        (candidate) => candidate.key == currentIssue.key,
      );
    } on TrackStateProviderException catch (error) {
      if (error is TrackStateRepositoryException) {
        rethrow;
      }
      throw TrackStateRepositoryException(
        'Could not archive ${currentIssue.key} because the repository provider '
        'failed while applying the archive change.',
      );
    }
  }

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async {
    await _acquireDeleteMutationLock();
    try {
      if (issue.storagePath.isEmpty) {
        throw const TrackStateRepositoryException(
          'This issue has no repository file path and cannot be deleted.',
        );
      }
      final permission = await _provider.getPermission();
      if (!permission.canWrite) {
        throw const TrackStateRepositoryException(
          'Connect a repository session with write access first.',
        );
      }
      final mutator = switch (_provider) {
        final RepositoryFileMutator supported => supported,
        _ => throw const TrackStateRepositoryException(
          'This repository provider does not support deleting issues yet.',
        ),
      };
      final snapshot = _snapshot ?? await loadSnapshot();
      final currentIssue = snapshot.issues.firstWhere(
        (candidate) => candidate.key == issue.key,
        orElse: () => issue,
      );
      final indexEntry = snapshot.repositoryIndex.entryForKey(currentIssue.key);
      if (indexEntry != null && indexEntry.childKeys.isNotEmpty) {
        throw TrackStateRepositoryException(
          'Cannot delete ${currentIssue.key} because it still has child issues: '
          '${indexEntry.childKeys.join(', ')}.',
        );
      }

      final writeBranch = await _provider.resolveWriteBranch();
      final tree = await _provider.listTree(ref: writeBranch);
      final blobPaths = tree
          .where((entry) => entry.type == 'blob')
          .map((entry) => entry.path)
          .toSet();
      final projectRoot = currentIssue.storagePath.split('/').first;
      if (projectRoot.isEmpty) {
        throw const TrackStateRepositoryException(
          'Could not resolve the project root for the issue being deleted.',
        );
      }
      final issueRoot = currentIssue.storagePath.substring(
        0,
        currentIssue.storagePath.lastIndexOf('/'),
      );
      final issueArtifactPaths =
          blobPaths
              .where(
                (path) =>
                    path == currentIssue.storagePath ||
                    path.startsWith('$issueRoot/'),
              )
              .toList()
            ..sort();
      if (issueArtifactPaths.isEmpty) {
        throw TrackStateRepositoryException(
          'Could not find repository artifacts for ${currentIssue.key}.',
        );
      }
      final tombstone = DeletedIssueTombstone(
        key: currentIssue.key,
        project: currentIssue.project,
        formerPath: currentIssue.storagePath,
        deletedAt: DateTime.now().toUtc().toIso8601String(),
        summary: currentIssue.summary,
        issueTypeId: currentIssue.issueTypeId.isEmpty
            ? null
            : currentIssue.issueTypeId,
        parentKey: currentIssue.parentKey,
        epicKey: currentIssue.epicKey,
      );
      _knownTombstoneKeys.add(tombstone.key);
      _knownTombstonesByKey[tombstone.key] = tombstone;
      final latestSnapshot = _snapshot ?? snapshot;
      final snapshotDeletedByKey = {
        for (final entry in latestSnapshot.repositoryIndex.deleted)
          entry.key: entry,
        ..._knownTombstonesByKey,
        tombstone.key: tombstone,
      };
      final snapshotDeletedTombstones = snapshotDeletedByKey.values.toList()
        ..sort((a, b) => a.key.compareTo(b.key));
      final remainingIssues = latestSnapshot.issues
          .where((candidate) => candidate.key != currentIssue.key)
          .toList(growable: false);
      final repositoryIndex = _deriveRepositoryIndex(
        remainingIssues,
        snapshotDeletedTombstones,
      );
      final indexedRemainingIssues = [
        for (final remainingIssue in remainingIssues)
          remainingIssue.withRepositoryIndex(
            repositoryIndex.entryForKey(remainingIssue.key),
          ),
      ]..sort((a, b) => a.key.compareTo(b.key));
      final updatedSnapshot = TrackerSnapshot(
        project: latestSnapshot.project,
        repositoryIndex: repositoryIndex,
        issues: indexedRemainingIssues,
      );

      final tombstoneArtifactPrefix = _joinPath(
        projectRoot,
        '.trackstate/tombstones/',
      );
      final tombstoneKeysInArtifacts = blobPaths
          .where(
            (path) =>
                path.startsWith(tombstoneArtifactPrefix) &&
                path.endsWith('.json'),
          )
          .map((path) => path.split('/').last.replaceAll('.json', ''))
          .toSet();
      final tombstoneKeysForIndex = <String>{
        ..._knownTombstoneKeys,
        ...tombstoneKeysInArtifacts,
      };
      final tombstoneIndexTombstones =
          snapshotDeletedTombstones
              .where((entry) => tombstoneKeysForIndex.contains(entry.key))
              .toList(growable: false)
            ..sort((a, b) => a.key.compareTo(b.key));

      final tombstoneIndexPath = _joinPath(
        projectRoot,
        '.trackstate/index/tombstones.json',
      );
      final issuesIndexPath = _joinPath(
        projectRoot,
        '.trackstate/index/issues.json',
      );
      final tombstoneArtifactPath = _tombstoneArtifactPath(
        projectRoot,
        tombstone.key,
      );
      final changes = <RepositoryFileChange>[
        for (final path in issueArtifactPaths)
          RepositoryDeleteFileChange(
            path: path,
            expectedRevision:
                _snapshotArtifactRevisions[path] ??
                await _existingArtifactRevision(
                  path: path,
                  ref: writeBranch,
                  blobPaths: blobPaths,
                ),
          ),
        RepositoryTextFileChange(
          path: issuesIndexPath,
          content:
              '${jsonEncode(_repositoryIndexEntriesJson(repositoryIndex.entries))}\n',
          expectedRevision: await _existingRevision(
            path: issuesIndexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
        RepositoryTextFileChange(
          path: tombstoneIndexPath,
          content:
              '${jsonEncode(_tombstoneIndexEntriesJson(projectRoot, tombstoneIndexTombstones))}\n',
          expectedRevision: await _existingRevision(
            path: tombstoneIndexPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
        RepositoryTextFileChange(
          path: tombstoneArtifactPath,
          content: '${jsonEncode(_deletedIssueTombstoneJson(tombstone))}\n',
          expectedRevision: await _existingRevision(
            path: tombstoneArtifactPath,
            ref: writeBranch,
            blobPaths: blobPaths,
          ),
        ),
      ];

      try {
        await mutator.applyFileChanges(
          RepositoryFileChangeRequest(
            branch: writeBranch,
            message: 'Delete ${currentIssue.key} and reserve tombstone',
            changes: changes,
          ),
        );
        _snapshot = updatedSnapshot;
        return tombstone;
      } catch (_) {
        _knownTombstoneKeys.remove(tombstone.key);
        _knownTombstonesByKey.remove(tombstone.key);
        rethrow;
      }
    } finally {
      _releaseDeleteMutationLock();
    }
  }

  Future<TrackerSnapshot> _loadSetupSnapshot() async {
    final loadWarnings = <String>[];
    final tree = await _provider.listTree(ref: _provider.dataRef);
    _snapshotTree = tree;
    final blobPaths = tree
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    _snapshotBlobPaths = blobPaths;
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
    final attachmentStorage = _resolveAttachmentStorage(projectJson);
    final supportedLocales = _resolveSupportedLocales(
      projectJson: projectJson,
      blobPaths: blobPaths,
      configRoot: configRoot,
      defaultLocale: defaultLocale,
    );
    final localizedLabels = await _loadLocalizedLabels(
      blobPaths: blobPaths,
      configRoot: configRoot,
      locales: supportedLocales,
    );
    final issueTypes = await _loadRequiredConfigEntries(
      _joinPath(configRoot, 'issue-types.json'),
      blobPaths: blobPaths,
      localizedLabels: localizedLabels['issueTypes'] ?? const {},
      loadWarnings: loadWarnings,
      warningSubject: 'issue types',
      fallbackEntries: _issueTypeDefinitions,
    );
    final statuses = await _loadRequiredConfigEntries(
      _joinPath(configRoot, 'statuses.json'),
      blobPaths: blobPaths,
      localizedLabels: localizedLabels['statuses'] ?? const {},
      loadWarnings: loadWarnings,
      warningSubject: 'statuses',
      fallbackEntries: _statusDefinitions,
    );
    final fields = await _getFieldDefinitions(
      _joinPath(configRoot, 'fields.json'),
      blobPaths: blobPaths,
      localizedLabels: localizedLabels['fields'] ?? const {},
      loadWarnings: loadWarnings,
    );
    final workflows = await _loadWorkflowDefinitions(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'workflows.json'),
      statusDefinitions: statuses,
    );
    final priorities = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'priorities.json'),
      localizedLabels: localizedLabels['priorities'] ?? const {},
    );
    final versions = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'versions.json'),
      localizedLabels: localizedLabels['versions'] ?? const {},
    );
    final components = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'components.json'),
      localizedLabels: localizedLabels['components'] ?? const {},
    );
    final resolutions = await _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'resolutions.json'),
      localizedLabels: localizedLabels['resolutions'] ?? const {},
    );
    final repositoryIndex = await _loadRepositoryIndex(
      blobPaths: blobPaths,
      dataRoot: dataRoot,
      issueTypeDefinitions: issueTypes,
    );
    final project = ProjectConfig(
      key: (projectJson['key'] as String?) ?? 'DEMO',
      name: (projectJson['name'] as String?) ?? 'TrackState Project',
      repository: _provider.repositoryLabel,
      branch: await _provider.resolveWriteBranch(),
      defaultLocale: defaultLocale,
      supportedLocales: supportedLocales,
      issueTypeDefinitions: issueTypes,
      statusDefinitions: statuses,
      fieldDefinitions: fields,
      workflowDefinitions: workflows,
      priorityDefinitions: priorities,
      versionDefinitions: versions,
      componentDefinitions: components,
      resolutionDefinitions: resolutions,
      attachmentStorage: attachmentStorage,
    );
    if (!usesLocalPersistence) {
      final summaryIssues = _loadHostedBootstrapIssues(
        dataRoot: dataRoot,
        tree: tree,
        repositoryIndex: repositoryIndex,
        project: project,
      );
      return TrackerSnapshot(
        project: project,
        issues: summaryIssues,
        repositoryIndex: _normalizeRepositoryIndex(
          repositoryIndex,
          summaryIssues,
        ),
        loadWarnings: loadWarnings,
        readiness: const TrackerBootstrapReadiness(
          domainStates: {
            TrackerDataDomain.projectMeta: TrackerLoadState.ready,
            TrackerDataDomain.issueSummaries: TrackerLoadState.ready,
            TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
            TrackerDataDomain.issueDetails: TrackerLoadState.partial,
          },
          sectionStates: {
            TrackerSectionKey.dashboard: TrackerLoadState.ready,
            TrackerSectionKey.board: TrackerLoadState.ready,
            TrackerSectionKey.search: TrackerLoadState.partial,
            TrackerSectionKey.hierarchy: TrackerLoadState.ready,
            TrackerSectionKey.settings: TrackerLoadState.ready,
          },
        ),
        startupRecovery: _startupRecovery,
      );
    }
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
      final attachments = await _loadAttachments(
        tree: tree,
        issueRoot: issueRoot,
      );
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
    return TrackerSnapshot(
      project: project,
      issues: indexedIssues,
      repositoryIndex: normalizedIndex,
      loadWarnings: loadWarnings,
      readiness: const TrackerBootstrapReadiness(
        domainStates: {
          TrackerDataDomain.projectMeta: TrackerLoadState.ready,
          TrackerDataDomain.issueSummaries: TrackerLoadState.ready,
          TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
          TrackerDataDomain.issueDetails: TrackerLoadState.ready,
        },
        sectionStates: {
          TrackerSectionKey.dashboard: TrackerLoadState.ready,
          TrackerSectionKey.board: TrackerLoadState.ready,
          TrackerSectionKey.search: TrackerLoadState.ready,
          TrackerSectionKey.hierarchy: TrackerLoadState.ready,
          TrackerSectionKey.settings: TrackerLoadState.ready,
        },
      ),
      startupRecovery: _startupRecovery,
    );
  }

  List<TrackStateIssue> _loadHostedBootstrapIssues({
    required String dataRoot,
    required List<RepositoryTreeEntry> tree,
    required RepositoryIndex repositoryIndex,
    required ProjectConfig project,
  }) {
    final issuePathsInTree =
        tree
            .where(
              (entry) =>
                  entry.type == 'blob' &&
                  entry.path.startsWith(dataRoot.isEmpty ? '' : '$dataRoot/') &&
                  entry.path.endsWith('/main.md'),
            )
            .map((entry) => entry.path)
            .toList()
          ..sort();
    _validateHostedBootstrapIndex(
      repositoryIndex: repositoryIndex,
      issuePathsInTree: issuePathsInTree,
    );
    final issues = <TrackStateIssue>[];
    for (final entry in repositoryIndex.entries) {
      if (entry.revision != null) {
        _snapshotArtifactRevisions[entry.path] = entry.revision;
      }
      issues.add(
        _parseSummaryIssue(
          entry: entry,
          projectKey: project.key,
          issueTypeDefinitions: project.issueTypeDefinitions,
          statusDefinitions: project.statusDefinitions,
          priorityDefinitions: project.priorityDefinitions,
        ),
      );
    }
    issues.sort((left, right) => left.key.compareTo(right.key));
    return [
      for (final issue in issues)
        issue.withRepositoryIndex(repositoryIndex.entryForKey(issue.key)),
    ];
  }

  void _validateHostedBootstrapIndex({
    required RepositoryIndex repositoryIndex,
    required List<String> issuePathsInTree,
  }) {
    if (repositoryIndex.entries.isEmpty) {
      throw const TrackStateRepositoryException(
        'Hosted bootstrap requires .trackstate/index/issues.json with summary entries. Regenerate the tracker indexes and retry.',
      );
    }
    for (final entry in repositoryIndex.entries) {
      if ((entry.summary ?? '').trim().isEmpty ||
          (entry.issueTypeId ?? '').trim().isEmpty ||
          (entry.statusId ?? '').trim().isEmpty ||
          (entry.updatedLabel ?? '').trim().isEmpty) {
        throw TrackStateRepositoryException(
          'Hosted bootstrap requires summary metadata for ${entry.key} in .trackstate/index/issues.json. Regenerate the tracker indexes and retry.',
        );
      }
    }
    final indexedPaths =
        repositoryIndex.entries.map((entry) => entry.path).toList()..sort();
    if (indexedPaths.length != issuePathsInTree.length) {
      throw const TrackStateRepositoryException(
        'Hosted bootstrap index is inconsistent with repository issue paths. Regenerate the tracker indexes and retry.',
      );
    }
    for (var index = 0; index < indexedPaths.length; index += 1) {
      if (indexedPaths[index] != issuePathsInTree[index]) {
        throw const TrackStateRepositoryException(
          'Hosted bootstrap index is inconsistent with repository issue paths. Regenerate the tracker indexes and retry.',
        );
      }
    }
  }

  bool _hasHydratedScopes(
    TrackStateIssue issue,
    Set<IssueHydrationScope> scopes,
  ) {
    for (final scope in scopes) {
      final isLoaded = switch (scope) {
        IssueHydrationScope.detail => issue.hasDetailLoaded,
        IssueHydrationScope.comments => issue.hasCommentsLoaded,
        IssueHydrationScope.attachments => issue.hasAttachmentsLoaded,
      };
      if (!isLoaded) {
        return false;
      }
    }
    return true;
  }

  Future<String?> _tryReadIssueAcceptance(String issueRoot) async {
    final acceptancePath = _joinPath(issueRoot, 'acceptance_criteria.md');
    if (!_snapshotBlobPaths.contains(acceptancePath)) {
      return null;
    }
    return _getRepositoryText(acceptancePath);
  }

  void _replaceIssueInSnapshot(TrackStateIssue issue) {
    final snapshot = _snapshot;
    if (snapshot == null) {
      return;
    }
    final updatedIssues = [
      for (final candidate in snapshot.issues)
        if (candidate.key == issue.key) issue else candidate,
    ]..sort((left, right) => left.key.compareTo(right.key));
    _snapshot = TrackerSnapshot(
      project: snapshot.project,
      issues: updatedIssues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
      readiness: snapshot.readiness,
    );
  }

  ProviderSession _syncProviderSession({
    required ProviderConnectionState connectionState,
    required String resolvedUserIdentity,
    required RepositoryPermission permission,
  }) {
    _session.update(
      providerType: _provider.providerType,
      connectionState: connectionState,
      resolvedUserIdentity: resolvedUserIdentity,
      canRead: permission.canRead,
      canWrite: permission.canWrite,
      canCreateBranch: permission.canCreateBranch,
      canManageAttachments: permission.canManageAttachments,
      attachmentUploadMode: permission.attachmentUploadMode,
      supportsReleaseAttachmentWrites:
          permission.supportsReleaseAttachmentWrites,
      canCheckCollaborators: permission.canCheckCollaborators,
    );
    return _session;
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

  ProjectAttachmentStorageSettings _resolveAttachmentStorage(
    Map<String, Object?> projectJson,
  ) {
    final rawAttachmentStorage = projectJson['attachmentStorage'];
    if (rawAttachmentStorage == null) {
      return usesLocalPersistence
          ? const ProjectAttachmentStorageSettings()
          : const ProjectAttachmentStorageSettings(
              mode: AttachmentStorageMode.githubReleases,
              githubReleases: GitHubReleasesAttachmentStorageSettings(
                tagPrefix:
                    GitHubReleasesAttachmentStorageSettings.defaultTagPrefix,
              ),
            );
    }
    if (rawAttachmentStorage is! Map) {
      throw const TrackStateRepositoryException(
        'project.json attachmentStorage must be a JSON object.',
      );
    }
    final attachmentStorage = rawAttachmentStorage.cast<Object?, Object?>();
    final mode = AttachmentStorageMode.tryParse(attachmentStorage['mode']);
    if (mode == null) {
      throw TrackStateRepositoryException(
        'project.json attachmentStorage.mode must be one of: '
        '${AttachmentStorageMode.values.map((value) => value.persistedValue).join(', ')}.',
      );
    }
    if (mode == AttachmentStorageMode.repositoryPath) {
      return const ProjectAttachmentStorageSettings(
        mode: AttachmentStorageMode.repositoryPath,
      );
    }
    final rawGitHubReleases = attachmentStorage['githubReleases'];
    if (rawGitHubReleases is! Map) {
      throw const TrackStateRepositoryException(
        'project.json attachmentStorage.githubReleases must be present when mode is github-releases.',
      );
    }
    final githubReleases = rawGitHubReleases.cast<Object?, Object?>();
    final tagPrefix = githubReleases['tagPrefix']?.toString().trim() ?? '';
    if (tagPrefix.isEmpty) {
      throw const TrackStateRepositoryException(
        'project.json attachmentStorage.githubReleases.tagPrefix is required when mode is github-releases.',
      );
    }
    return ProjectAttachmentStorageSettings(
      mode: AttachmentStorageMode.githubReleases,
      githubReleases: GitHubReleasesAttachmentStorageSettings(
        tagPrefix: tagPrefix,
      ),
    );
  }

  Future<String> _getRepositoryText(String path) async {
    final file = await _provider.readTextFile(path, ref: _provider.dataRef);
    _snapshotArtifactRevisions[path] = file.revision;
    return file.content;
  }

  Future<Object?> _getRepositoryJson(String path) async =>
      jsonDecode(await _getRepositoryText(path));

  Future<Set<String>> _persistedFieldIds({
    required String path,
    required String ref,
    required Set<String> blobPaths,
  }) async {
    if (!blobPaths.contains(path)) {
      return const <String>{};
    }
    try {
      final json = jsonDecode(
        (await _provider.readTextFile(path, ref: ref)).content,
      );
      if (json is! List) {
        return const <String>{};
      }
      return {
        for (final entry in json.whereType<Map>())
          if (_persistedFieldId(entry) case final id? when id.isNotEmpty) id,
      };
    } on FormatException {
      return const <String>{};
    }
  }

  List<String> _resolveSupportedLocales({
    required Map<String, Object?> projectJson,
    required Set<String> blobPaths,
    required String configRoot,
    required String defaultLocale,
  }) {
    final locales = <String>[];
    final configuredLocales = projectJson['supportedLocales'];
    if (configuredLocales is List) {
      for (final locale in configuredLocales) {
        final normalized = locale.toString().trim();
        if (normalized.isNotEmpty && !locales.contains(normalized)) {
          locales.add(normalized);
        }
      }
    }
    final i18nPrefix = _joinPath(configRoot, 'i18n/');
    for (final path in blobPaths) {
      if (!path.startsWith(i18nPrefix) || !path.endsWith('.json')) {
        continue;
      }
      final locale = path
          .substring(i18nPrefix.length, path.length - '.json'.length)
          .trim();
      if (locale.isNotEmpty && !locales.contains(locale)) {
        locales.add(locale);
      }
    }
    final normalizedDefaultLocale = defaultLocale.trim().isEmpty
        ? 'en'
        : defaultLocale.trim();
    if (!locales.contains(normalizedDefaultLocale)) {
      locales.insert(0, normalizedDefaultLocale);
    }
    return locales;
  }

  Future<Map<String, Map<String, Map<String, String>>>> _loadLocalizedLabels({
    required Set<String> blobPaths,
    required String configRoot,
    required List<String> locales,
  }) async {
    final result = <String, Map<String, Map<String, String>>>{};
    for (final locale in locales) {
      final path = _joinPath(configRoot, 'i18n/$locale.json');
      if (!blobPaths.contains(path)) {
        continue;
      }
      final json = await _getRepositoryJson(path);
      if (json is! Map) {
        continue;
      }
      for (final entry in json.entries) {
        final value = entry.value;
        if (value is! Map) continue;
        final localizedCatalog = result.putIfAbsent(
          entry.key.toString(),
          () => <String, Map<String, String>>{},
        );
        for (final localizedEntry in value.entries) {
          final key = localizedEntry.key.toString();
          final label = localizedEntry.value.toString().trim();
          if (key.isEmpty || label.isEmpty) {
            continue;
          }
          localizedCatalog.putIfAbsent(key, () => <String, String>{})[locale] =
              label;
        }
      }
    }
    return result;
  }

  Future<List<TrackStateConfigEntry>> _getConfigEntries(
    String path, {
    required Map<String, Map<String, String>> localizedLabels,
  }) async {
    return _configEntriesFromJson(
      await _getRepositoryJson(path),
      localizedLabels: localizedLabels,
    );
  }

  Future<List<TrackStateConfigEntry>> _loadRequiredConfigEntries(
    String path, {
    required Set<String> blobPaths,
    required Map<String, Map<String, String>> localizedLabels,
    required List<String> loadWarnings,
    required String warningSubject,
    required List<TrackStateConfigEntry> fallbackEntries,
  }) async {
    if (!blobPaths.contains(path)) {
      loadWarnings.add(
        'Falling back to built-in $warningSubject because $path is missing.',
      );
      return List<TrackStateConfigEntry>.from(fallbackEntries, growable: false);
    }
    try {
      return await _getConfigEntries(path, localizedLabels: localizedLabels);
    } on FormatException catch (error) {
      loadWarnings.add(
        'Falling back to built-in $warningSubject after failing to parse $path: $error',
      );
      return List<TrackStateConfigEntry>.from(fallbackEntries, growable: false);
    }
  }

  Future<List<TrackStateConfigEntry>> _loadOptionalConfigEntries({
    required Set<String> blobPaths,
    required String path,
    required Map<String, Map<String, String>> localizedLabels,
  }) async {
    if (!blobPaths.contains(path)) return const [];
    return _getConfigEntries(path, localizedLabels: localizedLabels);
  }

  Future<List<TrackStateFieldDefinition>> _getFieldDefinitions(
    String path, {
    required Set<String> blobPaths,
    required Map<String, Map<String, String>> localizedLabels,
    required List<String> loadWarnings,
  }) async {
    if (!blobPaths.contains(path)) {
      loadWarnings.add(
        'Falling back to built-in fields because $path is missing.',
      );
      return List<TrackStateFieldDefinition>.from(
        _fieldDefinitions,
        growable: false,
      );
    }
    try {
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
            final entryLocalizedLabels = localizedLabels[id] ?? const {};
            final optionsJson = entry['options'];
            final applicableIssueTypes = entry['issueTypes'];
            return TrackStateFieldDefinition(
              id: id,
              name: fallbackName,
              type: entry['type']?.toString() ?? 'string',
              required: entry['required'] == true,
              options: optionsJson is List
                  ? optionsJson
                        .whereType<Map>()
                        .map(
                          (option) => TrackStateFieldOption(
                            id:
                                option['id']?.toString() ??
                                _canonicalConfigId(option['name']?.toString()),
                            name:
                                option['name']?.toString() ??
                                option['id']?.toString() ??
                                '',
                          ),
                        )
                        .where(
                          (option) =>
                              option.id.isNotEmpty && option.name.isNotEmpty,
                        )
                        .toList(growable: false)
                  : const [],
              defaultValue: entry['defaultValue'],
              applicableIssueTypeIds: applicableIssueTypes is List
                  ? applicableIssueTypes
                        .map((value) => value.toString().trim())
                        .where((value) => value.isNotEmpty)
                        .toList(growable: false)
                  : const [],
              reserved: ProjectSettingsValidationService.reservedFieldIds
                  .contains(id),
              localizedLabels: entryLocalizedLabels,
            );
          })
          .toList(growable: false);
    } on FormatException catch (error) {
      loadWarnings.add(
        'Falling back to built-in fields after failing to parse $path: $error',
      );
      return List<TrackStateFieldDefinition>.from(
        _fieldDefinitions,
        growable: false,
      );
    }
  }

  Future<List<TrackStateWorkflowDefinition>> _loadWorkflowDefinitions({
    required Set<String> blobPaths,
    required String path,
    required List<TrackStateConfigEntry> statusDefinitions,
  }) async {
    if (!blobPaths.contains(path)) {
      return const [];
    }
    final json = await _getRepositoryJson(path);
    if (json is! Map) {
      return const [];
    }
    return json.entries
        .where((entry) => entry.value is Map)
        .map((entry) {
          final workflowJson = entry.value as Map;
          final statuses = workflowJson['statuses'];
          final transitions = workflowJson['transitions'];
          final workflowId = entry.key.toString();
          return TrackStateWorkflowDefinition(
            id: workflowId,
            name: workflowJson['name']?.toString() ?? workflowId,
            statusIds: statuses is List
                ? statuses
                      .map(
                        (value) =>
                            _matchingConfigEntry(
                              value?.toString() ?? '',
                              statusDefinitions,
                            )?.id ??
                            _canonicalConfigId(value?.toString()),
                      )
                      .where((value) => value.isNotEmpty)
                      .toList(growable: false)
                : const [],
            transitions: transitions is List
                ? transitions
                      .whereType<Map>()
                      .map(
                        (transition) => TrackStateWorkflowTransition(
                          id:
                              transition['id']?.toString() ??
                              _canonicalConfigId(
                                transition['name']?.toString(),
                              ),
                          name:
                              transition['name']?.toString() ??
                              transition['id']?.toString() ??
                              'Transition',
                          fromStatusId:
                              _matchingConfigEntry(
                                transition['from']?.toString() ?? '',
                                statusDefinitions,
                              )?.id ??
                              _canonicalConfigId(
                                transition['from']?.toString(),
                              ),
                          toStatusId:
                              _matchingConfigEntry(
                                transition['to']?.toString() ?? '',
                                statusDefinitions,
                              )?.id ??
                              _canonicalConfigId(transition['to']?.toString()),
                        ),
                      )
                      .where(
                        (transition) =>
                            transition.id.isNotEmpty &&
                            transition.fromStatusId.isNotEmpty &&
                            transition.toStatusId.isNotEmpty,
                      )
                      .toList(growable: false)
                : const [],
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
    final entries = <RepositoryIssueIndexEntry>[];
    if (blobPaths.contains(issuesPath)) {
      final json = await _getRepositoryJson(issuesPath);
      if (json is List) {
        entries.addAll(
          json
              .whereType<Map>()
              .map((entry) => _repositoryIndexEntry(entry))
              .where((entry) => blobPaths.contains(entry.path)),
        );
      }
    }
    final deleted = await _loadDeletedIssueTombstones(
      blobPaths: blobPaths,
      dataRoot: dataRoot,
      issueTypeDefinitions: issueTypeDefinitions,
    );
    return RepositoryIndex(entries: entries, deleted: deleted);
  }

  Future<List<DeletedIssueTombstone>> _loadDeletedIssueTombstones({
    required Set<String> blobPaths,
    required String dataRoot,
    required List<TrackStateConfigEntry> issueTypeDefinitions,
    bool includeLegacyDeletedIndex = true,
  }) async {
    final tombstonesPath = _joinPath(
      dataRoot,
      '.trackstate/index/tombstones.json',
    );
    final deletedPath = _joinPath(dataRoot, '.trackstate/index/deleted.json');
    final deleted = <DeletedIssueTombstone>[];
    if (blobPaths.contains(tombstonesPath)) {
      Object? json;
      try {
        json = await _getRepositoryJson(tombstonesPath);
      } on GitHubRateLimitException catch (error) {
        _captureHostedStartupRecovery(error);
        return _dedupeDeletedIssueTombstones(deleted);
      }
      if (json is List) {
        for (final entry in json.whereType<Map>()) {
          final tombstonePath =
              entry['path']?.toString() ?? entry['tombstonePath']?.toString();
          if (tombstonePath == null || tombstonePath.isEmpty) {
            deleted.add(
              _deletedIssueTombstone(
                entry,
                issueTypeDefinitions: issueTypeDefinitions,
              ),
            );
            continue;
          }
          Object? tombstoneJson;
          try {
            tombstoneJson = await _getRepositoryJson(tombstonePath);
          } on GitHubRateLimitException catch (error) {
            _captureHostedStartupRecovery(error);
            return _dedupeDeletedIssueTombstones(deleted);
          }
          if (tombstoneJson is! Map) {
            throw TrackStateRepositoryException(
              'Tombstone artifact $tombstonePath did not contain a JSON object.',
            );
          }
          deleted.add(
            _deletedIssueTombstone(
              tombstoneJson,
              issueTypeDefinitions: issueTypeDefinitions,
            ),
          );
        }
      }
    }
    if (includeLegacyDeletedIndex && blobPaths.contains(deletedPath)) {
      Object? json;
      try {
        json = await _getRepositoryJson(deletedPath);
      } on GitHubRateLimitException catch (error) {
        _captureHostedStartupRecovery(error);
        return _dedupeDeletedIssueTombstones(deleted);
      }
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
    return _dedupeDeletedIssueTombstones(deleted);
  }

  void _captureHostedStartupRecovery(GitHubRateLimitException error) {
    _startupRecovery ??= TrackerStartupRecovery(
      kind: TrackerStartupRecoveryKind.githubRateLimit,
      failedPath: error.requestPath,
      retryAfter: error.retryAfter,
    );
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

  Future<List<IssueAttachment>> _loadAttachments({
    required List<RepositoryTreeEntry> tree,
    required String issueRoot,
  }) async {
    final attachmentPrefix = _joinPath(issueRoot, 'attachments/');
    final attachmentMetadataPath = _attachmentMetadataPath(issueRoot);
    final attachmentsById = <String, IssueAttachment>{};
    if (_snapshotBlobPaths.contains(attachmentMetadataPath)) {
      final metadataJson = await _getRepositoryJson(attachmentMetadataPath);
      if (metadataJson is! List) {
        throw TrackStateRepositoryException(
          'Attachment metadata in $attachmentMetadataPath must be a JSON array.',
        );
      }
      for (final entry in metadataJson) {
        if (entry is! Map) {
          throw TrackStateRepositoryException(
            'Attachment metadata in $attachmentMetadataPath must contain only objects.',
          );
        }
        final attachment = _parseAttachmentMetadataEntry(
          entry.cast<Object?, Object?>(),
        );
        attachmentsById[attachment.id] = attachment;
      }
    }
    final historyReader = switch (_provider) {
      final RepositoryHistoryReader supported => supported,
      _ => null,
    };
    for (final entry in tree.where(
      (candidate) =>
          candidate.type == 'blob' &&
          candidate.path.startsWith(attachmentPrefix) &&
          candidate.path.length > attachmentPrefix.length,
    )) {
      final attachment = await _provider.readAttachment(
        entry.path,
        ref: _provider.dataRef,
      );
      List<RepositoryHistoryCommit> history = const <RepositoryHistoryCommit>[];
      if (historyReader != null) {
        try {
          history = await historyReader.listHistory(
            ref: _provider.dataRef,
            path: entry.path,
          );
        } on TrackStateProviderException {
          history = const <RepositoryHistoryCommit>[];
        }
      }
      final createdCommit = history.isEmpty ? null : history.last;
      _snapshotArtifactRevisions[entry.path] = attachment.revision;
      final existing = attachmentsById[entry.path];
      if (existing?.storageBackend == AttachmentStorageMode.githubReleases) {
        continue;
      }
      attachmentsById[entry.path] = IssueAttachment(
        id: existing?.id ?? entry.path,
        name: existing?.name ?? entry.path.split('/').last,
        mediaType: existing?.mediaType ?? _mediaTypeForPath(entry.path),
        sizeBytes:
            existing?.sizeBytes ??
            attachment.declaredSizeBytes ??
            attachment.bytes.length,
        author: existing?.author ?? createdCommit?.author ?? 'unknown',
        createdAt:
            existing?.createdAt ?? createdCommit?.timestamp ?? 'from repo',
        storagePath: existing?.storagePath ?? entry.path,
        revisionOrOid: _attachmentRevisionOrOid(
          attachment: attachment,
          isLfsTracked: attachment.lfsOid != null,
        ),
        storageBackend: AttachmentStorageMode.repositoryPath,
        repositoryPath: entry.path,
        githubReleaseTag: existing?.githubReleaseTag,
        githubReleaseAssetName: existing?.githubReleaseAssetName,
      );
    }
    return attachmentsById.values.toList()..sort(_sortAttachmentsNewestFirst);
  }

  Future<List<IssueHistoryEntry>> _normalizeIssueHistory({
    required TrackStateIssue issue,
    required List<RepositoryHistoryCommit> commits,
  }) async {
    final events = <IssueHistoryEntry>[];
    for (final commit in commits) {
      for (final change in commit.changes) {
        final changedPaths = [
          if (change.previousPath != null) change.previousPath!,
          change.path,
        ];
        final effectivePath = change.previousPath ?? change.path;
        if (effectivePath.endsWith('/main.md') ||
            change.path.endsWith('/main.md')) {
          final currentMainPath =
              change.changeType == RepositoryHistoryChangeType.removed
              ? null
              : change.path;
          final previousMainPath =
              change.changeType == RepositoryHistoryChangeType.added
              ? null
              : effectivePath;
          final currentState = currentMainPath == null
              ? null
              : await _loadHistoryIssueState(
                  ref: commit.sha,
                  mainPath: currentMainPath,
                );
          final previousState =
              commit.parentSha == null || previousMainPath == null
              ? null
              : await _loadHistoryIssueState(
                  ref: commit.parentSha!,
                  mainPath: previousMainPath,
                );
          if (previousState == null && currentState != null) {
            events.add(
              IssueHistoryEntry(
                commitSha: commit.sha,
                timestamp: commit.timestamp,
                author: commit.author,
                changeType: IssueHistoryChangeType.created,
                affectedEntity: IssueHistoryEntity.issue,
                affectedEntityId: currentState.key,
                summary: 'Created ${currentState.key}',
                changedPaths: changedPaths,
              ),
            );
            continue;
          }
          if (previousState == null || currentState == null) {
            continue;
          }
          if (previousState.isArchived != currentState.isArchived) {
            events.add(
              IssueHistoryEntry(
                commitSha: commit.sha,
                timestamp: commit.timestamp,
                author: commit.author,
                changeType: currentState.isArchived
                    ? IssueHistoryChangeType.archived
                    : IssueHistoryChangeType.restored,
                affectedEntity: IssueHistoryEntity.issue,
                affectedEntityId: currentState.key,
                summary: currentState.isArchived
                    ? 'Archived ${currentState.key}'
                    : 'Restored ${currentState.key}',
                changedPaths: changedPaths,
                before: previousState.isArchived.toString(),
                after: currentState.isArchived.toString(),
              ),
            );
          }
          if (previousMainPath != change.path ||
              previousState.parentKey != currentState.parentKey ||
              previousState.epicKey != currentState.epicKey) {
            events.add(
              IssueHistoryEntry(
                commitSha: commit.sha,
                timestamp: commit.timestamp,
                author: commit.author,
                changeType: IssueHistoryChangeType.moved,
                affectedEntity: IssueHistoryEntity.hierarchy,
                affectedEntityId: currentState.key,
                summary: 'Moved ${currentState.key} in the hierarchy',
                changedPaths: changedPaths,
                before:
                    previousState.parentKey ??
                    previousState.epicKey ??
                    previousMainPath,
                after:
                    currentState.parentKey ??
                    currentState.epicKey ??
                    change.path,
              ),
            );
          }
          _addHistoryFieldEvent(
            events,
            commit: commit,
            changedPaths: changedPaths,
            issueKey: currentState.key,
            fieldName: 'summary',
            before: previousState.summary,
            after: currentState.summary,
          );
          _addHistoryFieldEvent(
            events,
            commit: commit,
            changedPaths: changedPaths,
            issueKey: currentState.key,
            fieldName: 'description',
            before: previousState.description,
            after: currentState.description,
          );
          _addHistoryFieldEvent(
            events,
            commit: commit,
            changedPaths: changedPaths,
            issueKey: currentState.key,
            fieldName: 'status',
            before: previousState.statusId,
            after: currentState.statusId,
          );
          _addHistoryFieldEvent(
            events,
            commit: commit,
            changedPaths: changedPaths,
            issueKey: currentState.key,
            fieldName: 'priority',
            before: previousState.priorityId,
            after: currentState.priorityId,
          );
          _addHistoryFieldEvent(
            events,
            commit: commit,
            changedPaths: changedPaths,
            issueKey: currentState.key,
            fieldName: 'assignee',
            before: previousState.assignee,
            after: currentState.assignee,
          );
          _addHistoryFieldEvent(
            events,
            commit: commit,
            changedPaths: changedPaths,
            issueKey: currentState.key,
            fieldName: 'labels',
            before: previousState.labels.join(', '),
            after: currentState.labels.join(', '),
          );
          _addHistoryFieldEvent(
            events,
            commit: commit,
            changedPaths: changedPaths,
            issueKey: currentState.key,
            fieldName: 'acceptanceCriteria',
            before: previousState.acceptanceCriteria.join('\n'),
            after: currentState.acceptanceCriteria.join('\n'),
          );
          continue;
        }
        if (_isIssueCommentPath(effectivePath)) {
          final commentId = effectivePath.split('/').last.replaceAll('.md', '');
          final currentMarkdown =
              change.changeType == RepositoryHistoryChangeType.removed
              ? null
              : await _tryReadTextAtRef(change.path, commit.sha);
          final previousMarkdown =
              commit.parentSha == null ||
                  change.changeType == RepositoryHistoryChangeType.added
              ? null
              : await _tryReadTextAtRef(effectivePath, commit.parentSha!);
          final currentComment = currentMarkdown == null
              ? null
              : _parseComment(change.path, currentMarkdown);
          final previousComment = previousMarkdown == null
              ? null
              : _parseComment(effectivePath, previousMarkdown);
          if (change.changeType == RepositoryHistoryChangeType.added) {
            events.add(
              IssueHistoryEntry(
                commitSha: commit.sha,
                timestamp: commit.timestamp,
                author: commit.author,
                changeType: IssueHistoryChangeType.added,
                affectedEntity: IssueHistoryEntity.comment,
                affectedEntityId: commentId,
                summary: 'Added comment $commentId',
                changedPaths: changedPaths,
                after: currentComment?.body,
              ),
            );
          } else if (change.changeType == RepositoryHistoryChangeType.removed) {
            events.add(
              IssueHistoryEntry(
                commitSha: commit.sha,
                timestamp: commit.timestamp,
                author: commit.author,
                changeType: IssueHistoryChangeType.removed,
                affectedEntity: IssueHistoryEntity.comment,
                affectedEntityId: commentId,
                summary: 'Removed comment $commentId',
                changedPaths: changedPaths,
                before: previousComment?.body,
              ),
            );
          } else if (previousComment != null &&
              currentComment != null &&
              previousComment.body != currentComment.body) {
            events.add(
              IssueHistoryEntry(
                commitSha: commit.sha,
                timestamp: commit.timestamp,
                author: commit.author,
                changeType: IssueHistoryChangeType.updated,
                affectedEntity: IssueHistoryEntity.comment,
                affectedEntityId: currentComment.id,
                summary: 'Updated comment ${currentComment.id}',
                changedPaths: changedPaths,
                before: previousComment.body,
                after: currentComment.body,
              ),
            );
          }
          continue;
        }
        if (_isIssueAttachmentPath(effectivePath)) {
          final currentSegments = change.path.split('/');
          final previousSegments = effectivePath.split('/');
          final attachmentName = currentSegments.isNotEmpty
              ? currentSegments.last
              : previousSegments.isNotEmpty
              ? previousSegments.last
              : 'attachment';
          events.add(
            IssueHistoryEntry(
              commitSha: commit.sha,
              timestamp: commit.timestamp,
              author: commit.author,
              changeType: switch (change.changeType) {
                RepositoryHistoryChangeType.added =>
                  IssueHistoryChangeType.added,
                RepositoryHistoryChangeType.removed =>
                  IssueHistoryChangeType.removed,
                RepositoryHistoryChangeType.renamed =>
                  IssueHistoryChangeType.moved,
                RepositoryHistoryChangeType.modified =>
                  IssueHistoryChangeType.updated,
              },
              affectedEntity: IssueHistoryEntity.attachment,
              affectedEntityId: attachmentName,
              summary: switch (change.changeType) {
                RepositoryHistoryChangeType.added =>
                  'Added attachment $attachmentName',
                RepositoryHistoryChangeType.removed =>
                  'Removed attachment $attachmentName',
                RepositoryHistoryChangeType.renamed =>
                  'Moved attachment $attachmentName',
                RepositoryHistoryChangeType.modified =>
                  'Updated attachment $attachmentName',
              },
              changedPaths: changedPaths,
              before: change.previousPath,
              after: change.path,
            ),
          );
        }
      }
    }
    return events
        .where(
          (entry) =>
              entry.affectedEntity == IssueHistoryEntity.issue ||
              entry.summary.contains(issue.key) ||
              entry.changedPaths.any((path) => path.contains('/${issue.key}/')),
        )
        .toList(growable: false);
  }

  void _addHistoryFieldEvent(
    List<IssueHistoryEntry> events, {
    required RepositoryHistoryCommit commit,
    required List<String> changedPaths,
    required String issueKey,
    required String fieldName,
    required String before,
    required String after,
  }) {
    if (before == after) {
      return;
    }
    events.add(
      IssueHistoryEntry(
        commitSha: commit.sha,
        timestamp: commit.timestamp,
        author: commit.author,
        changeType: IssueHistoryChangeType.updated,
        affectedEntity: IssueHistoryEntity.issue,
        affectedEntityId: issueKey,
        fieldName: fieldName,
        before: before,
        after: after,
        summary: 'Updated $fieldName on $issueKey',
        changedPaths: changedPaths,
      ),
    );
  }

  Future<_HistoryIssueState?> _loadHistoryIssueState({
    required String ref,
    required String mainPath,
  }) async {
    final markdown = await _tryReadTextAtRef(mainPath, ref);
    if (markdown == null) {
      return null;
    }
    final acceptancePath = _joinPath(
      mainPath.substring(0, mainPath.lastIndexOf('/')),
      'acceptance_criteria.md',
    );
    final acceptanceMarkdown = await _tryReadTextAtRef(acceptancePath, ref);
    final frontmatter = _frontmatter(markdown);
    final body = _body(markdown);
    return _HistoryIssueState(
      key: frontmatter['key']?.toString() ?? 'UNKNOWN-0',
      summary: (frontmatter['summary']?.toString() ?? '')
          .ifEmpty(_section(body, 'Summary'))
          .ifEmpty('Untitled issue'),
      description: _section(
        body,
        'Description',
      ).ifEmpty(_section(body, 'Summary')),
      statusId: _canonicalConfigId(frontmatter['status']?.toString()),
      priorityId: _canonicalConfigId(frontmatter['priority']?.toString()),
      assignee: frontmatter['assignee']?.toString() ?? '',
      labels: _stringList(frontmatter['labels']),
      parentKey: _nullable(frontmatter['parent']?.toString()),
      epicKey: _nullable(frontmatter['epic']?.toString()),
      isArchived: _boolValue(frontmatter['archived']) ?? false,
      acceptanceCriteria: acceptanceMarkdown == null
          ? const <String>[]
          : LineSplitter.split(acceptanceMarkdown)
                .where((line) => line.trimLeft().startsWith('- '))
                .map((line) => line.trimLeft().substring(2).trim())
                .toList(growable: false),
    );
  }

  Future<String?> _tryReadTextAtRef(String path, String ref) async {
    try {
      return (await _provider.readTextFile(path, ref: ref)).content;
    } on TrackStateProviderException {
      return null;
    }
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
      );
    } on TrackStateProviderException {
      return _snapshot?.project.statusDefinitions ?? const [];
    }
  }

  Future<String?> _existingRevision({
    required String path,
    required String ref,
    required Set<String> blobPaths,
  }) async {
    if (!blobPaths.contains(path)) {
      return null;
    }
    final file = await _provider.readTextFile(path, ref: ref);
    return file.revision;
  }

  Future<String?> _existingArtifactRevision({
    required String path,
    required String ref,
    required Set<String> blobPaths,
  }) async {
    if (!blobPaths.contains(path)) {
      return null;
    }
    final artifact = await _provider.readAttachment(path, ref: ref);
    return artifact.revision;
  }

  void _rebuildCachedArtifactRevisions({
    required TrackerSnapshot? previousSnapshot,
    required TrackerSnapshot? nextSnapshot,
    required Set<String> blobPaths,
  }) {
    final previousRevisions = Map<String, String?>.from(
      _snapshotArtifactRevisions,
    );
    _snapshotArtifactRevisions
      ..clear()
      ..addEntries(
        previousRevisions.entries.where(
          (entry) => blobPaths.contains(entry.key),
        ),
      );

    if (nextSnapshot != null) {
      for (final entry in nextSnapshot.repositoryIndex.entries) {
        if (entry.revision != null && blobPaths.contains(entry.path)) {
          _snapshotArtifactRevisions[entry.path] = entry.revision;
        }
      }
    }
    if (previousSnapshot == null || nextSnapshot == null) {
      return;
    }

    TrackStateIssue? issueForArtifactPath(
      Map<String, TrackStateIssue> issuesByKey,
      String path,
    ) {
      TrackStateIssue? bestMatch;
      for (final issue in issuesByKey.values) {
        if (issue.storagePath.isEmpty) {
          continue;
        }
        final issueRoot = _issueRoot(issue.storagePath);
        if (path == issue.storagePath || path.startsWith('$issueRoot/')) {
          if (bestMatch == null ||
              issueRoot.length > _issueRoot(bestMatch.storagePath).length) {
            bestMatch = issue;
          }
        }
      }
      return bestMatch;
    }

    final previousIssuesByKey = {
      for (final issue in previousSnapshot.issues)
        if (issue.storagePath.isNotEmpty) issue.key: issue,
    };
    final nextIssuesByKey = {
      for (final issue in nextSnapshot.issues)
        if (issue.storagePath.isNotEmpty) issue.key: issue,
    };
    for (final entry in previousRevisions.entries) {
      final previousIssue = issueForArtifactPath(
        previousIssuesByKey,
        entry.key,
      );
      if (previousIssue == null) {
        continue;
      }
      final nextIssue = nextIssuesByKey[previousIssue.key];
      if (nextIssue == null) {
        continue;
      }
      final previousRoot = _issueRoot(previousIssue.storagePath);
      final nextRoot = _issueRoot(nextIssue.storagePath);
      final rebasedPath = entry.key == previousIssue.storagePath
          ? nextIssue.storagePath
          : '$nextRoot${entry.key.substring(previousRoot.length)}';
      if (!blobPaths.contains(rebasedPath)) {
        continue;
      }
      _snapshotArtifactRevisions[rebasedPath] = entry.value;
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
  const DemoTrackStateRepository({
    TrackerSnapshot snapshot = _snapshot,
    JqlSearchService searchService = const JqlSearchService(),
  }) : _snapshotOverride = snapshot,
       _searchService = searchService;

  final TrackerSnapshot _snapshotOverride;
  final JqlSearchService _searchService;

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshotOverride;

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    final normalizedSummary = summary.trim();
    if (normalizedSummary.isEmpty) {
      throw const TrackStateRepositoryException(
        'Issue summary is required before creating an issue.',
      );
    }
    final key = _nextIssueKey(_snapshotOverride);
    final issuePath = _nextIssuePath(_snapshotOverride, key);
    final createdAt = DateTime.now().toUtc().toIso8601String();
    return _parseIssue(
      storagePath: issuePath,
      markdown: _buildIssueMarkdown(
        key: key,
        projectKey: _snapshotOverride.project.key,
        summary: normalizedSummary,
        description: description.trim(),
        customFields: customFields,
        issueTypeId: _defaultIssueTypeId(_snapshotOverride.project),
        statusId: _defaultStatusId(_snapshotOverride.project),
        priorityId: _defaultPriorityId(_snapshotOverride.project),
        assignee: 'demo-user',
        reporter: 'demo-user',
        createdAt: createdAt,
      ),
      comments: const [],
      links: const [],
      attachments: const [],
      repositoryIndexEntry: RepositoryIssueIndexEntry(
        key: key,
        path: issuePath,
        childKeys: const [],
      ),
      issueTypeDefinitions: _snapshotOverride.project.issueTypeDefinitions,
      statusDefinitions: _snapshotOverride.project.statusDefinitions,
      priorityDefinitions: _snapshotOverride.project.priorityDefinitions,
      resolutionDefinitions: _snapshotOverride.project.resolutionDefinitions,
    );
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => _searchService.search(
    issues: _snapshotOverride.issues,
    project: _snapshotOverride.project,
    jql: jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Demo repository is read-only and cannot archive issues.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Demo repository is read-only and cannot delete issues.',
      );

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

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue.copyWith(
    comments: [
      ...issue.comments,
      IssueComment(
        id: (issue.comments.length + 1).toString().padLeft(4, '0'),
        author: 'demo-user',
        body: body.trimRight(),
        updatedLabel: 'just now',
        createdAt: DateTime.now().toUtc().toIso8601String(),
        updatedAt: DateTime.now().toUtc().toIso8601String(),
        storagePath:
            '${_issueRoot(issue.storagePath)}/comments/${(issue.comments.length + 1).toString().padLeft(4, '0')}.md',
      ),
    ],
  );

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async {
    final attachmentPath = resolveIssueAttachmentPath(issue, name);
    final updatedAttachment = IssueAttachment(
      id: attachmentPath,
      name: attachmentPath.split('/').last,
      mediaType: _mediaTypeForPath(attachmentPath),
      sizeBytes: bytes.length,
      author: 'demo-user',
      createdAt: DateTime.now().toUtc().toIso8601String(),
      storagePath: attachmentPath,
      revisionOrOid: 'demo-revision',
    );
    return issue.copyWith(
      attachments: [
        for (final candidate in issue.attachments)
          if (candidate.storagePath == attachmentPath)
            updatedAttachment
          else
            candidate,
        if (!issue.attachments.any(
          (candidate) => candidate.storagePath == attachmentPath,
        ))
          updatedAttachment,
      ]..sort(_sortAttachmentsNewestFirst),
    );
  }

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List.fromList(utf8.encode('<svg />'));

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => [
    IssueHistoryEntry(
      commitSha: 'demo-commit',
      timestamp: '2026-05-05T00:10:00Z',
      author: 'ana',
      changeType: IssueHistoryChangeType.updated,
      affectedEntity: IssueHistoryEntity.issue,
      affectedEntityId: issue.key,
      fieldName: 'description',
      before: 'Old description',
      after: issue.description,
      summary: 'Updated description on ${issue.key}',
      changedPaths: [issue.storagePath],
    ),
  ];
}

class TrackStateRepositoryException extends TrackStateProviderException {
  const TrackStateRepositoryException(super.message);
}

class _HistoryIssueState {
  const _HistoryIssueState({
    required this.key,
    required this.summary,
    required this.description,
    required this.statusId,
    required this.priorityId,
    required this.assignee,
    required this.labels,
    required this.parentKey,
    required this.epicKey,
    required this.isArchived,
    required this.acceptanceCriteria,
  });

  final String key;
  final String summary;
  final String description;
  final String statusId;
  final String priorityId;
  final String assignee;
  final List<String> labels;
  final String? parentKey;
  final String? epicKey;
  final bool isArchived;
  final List<String> acceptanceCriteria;
}

TrackStateIssue _parseSummaryIssue({
  required RepositoryIssueIndexEntry entry,
  required String projectKey,
  required List<TrackStateConfigEntry> issueTypeDefinitions,
  required List<TrackStateConfigEntry> statusDefinitions,
  required List<TrackStateConfigEntry> priorityDefinitions,
}) {
  final issueTypeId = entry.issueTypeId ?? 'story';
  final statusId = entry.statusId ?? 'todo';
  final priorityId = entry.priorityId ?? 'medium';
  final status = _issueStatus(statusId, statusDefinitions);
  return TrackStateIssue(
    key: entry.key,
    project: projectKey,
    issueType: _issueType(issueTypeId, issueTypeDefinitions),
    issueTypeId: issueTypeId,
    status: status,
    statusId: statusId,
    priority: _issuePriority(priorityId, priorityDefinitions),
    priorityId: priorityId,
    summary: (entry.summary ?? '').ifEmpty('Untitled issue'),
    description: '',
    assignee: entry.assignee ?? 'unassigned',
    reporter: 'unknown',
    labels: entry.labels,
    components: const [],
    fixVersionIds: const [],
    watchers: const [],
    customFields: const {},
    parentKey: entry.parentKey,
    epicKey: entry.epicKey,
    parentPath: entry.parentPath,
    epicPath: entry.epicPath,
    progress: entry.progress ?? (status == IssueStatus.done ? 1 : .35),
    updatedLabel: entry.updatedLabel ?? 'from repo',
    acceptanceCriteria: const [],
    comments: const [],
    links: const [],
    attachments: const [],
    isArchived: entry.isArchived,
    hasDetailLoaded: false,
    hasCommentsLoaded: false,
    hasAttachmentsLoaded: false,
    resolutionId: entry.resolutionId,
    storagePath: entry.path,
  );
}

String? _acceptanceCriteriaMarkdown(List<String> criteria) {
  if (criteria.isEmpty) {
    return null;
  }
  return '${criteria.map((entry) => '- $entry').join('\n')}\n';
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
    hasDetailLoaded: true,
    hasCommentsLoaded: true,
    hasAttachmentsLoaded: true,
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
  final header = '# $title';
  final start = markdown.indexOf(header);
  if (start == -1) return '';
  final contentStart = markdown.indexOf('\n', start);
  if (contentStart == -1) return '';
  final nextHeaderStart = markdown.indexOf('\n# ', contentStart + 1);
  final content = nextHeaderStart == -1
      ? markdown.substring(contentStart + 1)
      : markdown.substring(contentStart + 1, nextHeaderStart);
  return content.trim();
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
  final header = '# $title';
  final start = markdown.indexOf(header);
  if (start != -1) {
    final nextHeaderStart = markdown.indexOf('\n# ', start + header.length);
    final prefix = markdown.substring(0, start);
    final replacement = '# $title\n\n$normalizedContent';
    if (nextHeaderStart == -1) {
      return '$prefix$replacement';
    }
    final suffix = markdown.substring(nextHeaderStart + 1);
    return '$prefix$replacement\n\n$suffix';
  }
  final trimmed = markdown.trimRight();
  final separator = trimmed.isEmpty ? '' : '\n\n';
  return '$trimmed$separator# $title\n\n$normalizedContent\n';
}

List<Map<String, Object?>> _settingsStatusesJson(
  List<TrackStateConfigEntry> statuses,
) => [
  for (final status in statuses)
    {
      'id': status.id.trim(),
      'name': status.name.trim(),
      if (status.category case final category? when category.trim().isNotEmpty)
        'category': category.trim(),
    },
];

List<Map<String, Object?>> _settingsConfigEntriesJson(
  List<TrackStateConfigEntry> entries,
) => [
  for (final entry in entries)
    {'id': entry.id.trim(), 'name': entry.name.trim()},
];

List<Map<String, Object?>> _settingsIssueTypesJson(
  List<TrackStateConfigEntry> issueTypes,
) => [
  for (final issueType in issueTypes)
    {
      'id': issueType.id.trim(),
      'name': issueType.name.trim(),
      if (issueType.hierarchyLevel case final hierarchyLevel?)
        'hierarchyLevel': hierarchyLevel,
      if (issueType.icon case final icon? when icon.trim().isNotEmpty)
        'icon': icon.trim(),
      if (issueType.workflowId case final workflowId?
          when workflowId.trim().isNotEmpty)
        'workflow': workflowId.trim(),
    },
];

List<Map<String, Object?>> _settingsFieldsJson(
  List<TrackStateFieldDefinition> fields,
) => [
  for (final field in fields)
    {
      'id': field.id.trim(),
      'name': field.name.trim(),
      'type': field.type.trim(),
      'required': field.required,
      if (field.options.isNotEmpty)
        'options': [
          for (final option in field.options)
            {'id': option.id.trim(), 'name': option.name.trim()},
        ],
      if (field.defaultValue != null) 'defaultValue': field.defaultValue,
      if (field.applicableIssueTypeIds.isNotEmpty)
        'issueTypes': [
          for (final issueTypeId in field.applicableIssueTypeIds)
            issueTypeId.trim(),
        ],
    },
];

List<TrackStateFieldDefinition> _persistedFieldDefinitions(
  List<TrackStateFieldDefinition> fields, {
  required Set<String> persistedFieldIds,
}) => [
  for (final field in fields)
    if (!field.reserved || persistedFieldIds.contains(field.id.trim())) field,
];

Map<String, Object?> _settingsWorkflowsJson(
  List<TrackStateWorkflowDefinition> workflows,
) => {
  for (final workflow in workflows)
    workflow.id.trim(): {
      'name': workflow.name.trim(),
      'statuses': [for (final statusId in workflow.statusIds) statusId.trim()],
      'transitions': [
        for (final transition in workflow.transitions)
          {
            'id': transition.id.trim(),
            'name': transition.name.trim(),
            'from': transition.fromStatusId.trim(),
            'to': transition.toStatusId.trim(),
          },
      ],
    },
};

Map<String, Object?> _settingsProjectJson(
  Map<String, Object?> currentProjectJson,
  ProjectSettingsCatalog settings,
) => <String, Object?>{
  ...currentProjectJson,
  'defaultLocale': settings.defaultLocale,
  'supportedLocales': settings.effectiveSupportedLocales,
  'attachmentStorage': _attachmentStorageProjectJson(
    settings.attachmentStorage,
  ),
};

Map<String, Object?> _attachmentStorageProjectJson(
  ProjectAttachmentStorageSettings storage,
) {
  return switch (storage.mode) {
    AttachmentStorageMode.repositoryPath => <String, Object?>{
      'mode': AttachmentStorageMode.repositoryPath.persistedValue,
    },
    AttachmentStorageMode.githubReleases => <String, Object?>{
      'mode': AttachmentStorageMode.githubReleases.persistedValue,
      'githubReleases': <String, Object?>{
        'tagPrefix': storage.githubReleases!.tagPrefix,
      },
    },
  };
}

Map<String, Object?> _localizedLabelsJson(
  ProjectSettingsCatalog settings,
  String locale,
) => <String, Object?>{
  'issueTypes': _configLocalizedLabelsJson(
    settings.issueTypeDefinitions,
    locale,
  ),
  'statuses': _configLocalizedLabelsJson(settings.statusDefinitions, locale),
  'fields': _fieldLocalizedLabelsJson(settings.fieldDefinitions, locale),
  'priorities': _configLocalizedLabelsJson(
    settings.priorityDefinitions,
    locale,
  ),
  'versions': _configLocalizedLabelsJson(settings.versionDefinitions, locale),
  'components': _configLocalizedLabelsJson(
    settings.componentDefinitions,
    locale,
  ),
  'resolutions': _configLocalizedLabelsJson(
    settings.resolutionDefinitions,
    locale,
  ),
};

Map<String, Object?> _configLocalizedLabelsJson(
  List<TrackStateConfigEntry> entries,
  String locale,
) => {
  for (final entry in entries)
    if (entry.localizedLabels[locale] case final label?
        when label.trim().isNotEmpty)
      entry.id.trim(): label.trim(),
};

Map<String, Object?> _fieldLocalizedLabelsJson(
  List<TrackStateFieldDefinition> fields,
  String locale,
) => {
  for (final field in fields)
    if (field.localizedLabels[locale] case final label?
        when label.trim().isNotEmpty)
      field.id.trim(): label.trim(),
};

String? _persistedFieldId(Map entry) {
  final explicitId = entry['id']?.toString().trim();
  if (explicitId != null && explicitId.isNotEmpty) {
    return explicitId;
  }
  final canonicalId = _canonicalConfigId(entry['name']?.toString());
  return canonicalId.isEmpty ? null : canonicalId;
}

List<TrackStateConfigEntry> _configEntriesFromJson(
  Object? json, {
  required Map<String, Map<String, String>> localizedLabels,
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
        final entryLocalizedLabels = localizedLabels[id] ?? const {};
        return TrackStateConfigEntry(
          id: id,
          name: fallbackName,
          category: entry['category']?.toString(),
          hierarchyLevel: entry['hierarchyLevel'] is num
              ? (entry['hierarchyLevel'] as num).toInt()
              : int.tryParse(entry['hierarchyLevel']?.toString() ?? ''),
          icon: entry['icon']?.toString(),
          workflowId:
              entry['workflow']?.toString() ?? entry['workflowId']?.toString(),
          localizedLabels: entryLocalizedLabels,
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

String _nextIssueKey(TrackerSnapshot snapshot) {
  var highest = 0;
  final keyPattern = RegExp('^${RegExp.escape(snapshot.project.key)}-(\\d+)\$');
  for (final issue in snapshot.issues) {
    final match = keyPattern.firstMatch(issue.key);
    final value = int.tryParse(match?.group(1) ?? '');
    if (value != null && value > highest) {
      highest = value;
    }
  }
  for (final deleted in snapshot.repositoryIndex.deleted) {
    final match = keyPattern.firstMatch(deleted.key);
    final value = int.tryParse(match?.group(1) ?? '');
    if (value != null && value > highest) {
      highest = value;
    }
  }
  return '${snapshot.project.key}-${highest + 1}';
}

String _nextIssuePath(TrackerSnapshot snapshot, String key) {
  final existingPath = snapshot.issues
      .map((issue) => issue.storagePath)
      .firstWhere(
        (path) => path.contains('/'),
        orElse: () => '${snapshot.project.key}/main.md',
      );
  final root = existingPath.split('/').first;
  return '$root/$key/main.md';
}

String _defaultIssueTypeId(ProjectConfig project) =>
    _firstMatchingConfigId(project.issueTypeDefinitions, {'story'}) ??
    project.issueTypeDefinitions.firstOrNull?.id ??
    'story';

String _defaultStatusId(ProjectConfig project) =>
    _firstMatchingConfigId(project.statusDefinitions, {'todo', 'to-do'}) ??
    project.statusDefinitions.firstOrNull?.id ??
    'todo';

String _defaultPriorityId(ProjectConfig project) =>
    _firstMatchingConfigId(project.priorityDefinitions, {'medium'}) ??
    project.priorityDefinitions.firstOrNull?.id ??
    'medium';

String? _firstMatchingConfigId(
  List<TrackStateConfigEntry> definitions,
  Set<String> preferredTokens,
) {
  for (final definition in definitions) {
    final idToken = _canonicalConfigId(definition.id);
    final nameToken = _canonicalConfigId(definition.name);
    if (preferredTokens.contains(idToken) ||
        preferredTokens.contains(nameToken)) {
      return definition.id;
    }
  }
  return null;
}

String _defaultAuthor(String? resolvedUserIdentity) {
  final normalized = (resolvedUserIdentity ?? '').trim();
  if (normalized.isEmpty || normalized.startsWith('/')) {
    return 'unassigned';
  }
  return normalized;
}

String _buildIssueMarkdown({
  required String key,
  required String projectKey,
  required String summary,
  required String description,
  Map<String, String> customFields = const {},
  required String issueTypeId,
  required String statusId,
  required String priorityId,
  required String assignee,
  required String reporter,
  required String createdAt,
}) {
  final normalizedCustomFields = Map<String, String>.fromEntries(
    customFields.entries.toList()
      ..sort((left, right) => left.key.compareTo(right.key)),
  );
  final buffer = StringBuffer()
    ..writeln('---')
    ..writeln('key: $key')
    ..writeln('project: $projectKey')
    ..writeln('issueType: $issueTypeId')
    ..writeln('status: $statusId')
    ..writeln('priority: $priorityId')
    ..writeln('summary: ${_yamlScalar(summary)}')
    ..writeln('assignee: ${_yamlScalar(assignee)}')
    ..writeln('reporter: ${_yamlScalar(reporter)}');
  if (normalizedCustomFields.isNotEmpty) {
    buffer.writeln('customFields: ${jsonEncode(normalizedCustomFields)}');
  }
  buffer
    ..writeln('created: $createdAt')
    ..writeln('updated: $createdAt')
    ..writeln('---')
    ..writeln()
    ..writeln('# Summary')
    ..writeln()
    ..writeln(summary)
    ..writeln()
    ..writeln('# Description')
    ..writeln()
    ..writeln(description.isEmpty ? 'Describe the issue.' : description);
  return '${buffer.toString().trimRight()}\n';
}

String _buildCommentMarkdown({
  required String author,
  required String createdAt,
  required String body,
}) {
  final buffer = StringBuffer()
    ..writeln('---')
    ..writeln('author: ${_yamlScalar(author)}')
    ..writeln('created: $createdAt')
    ..writeln('updated: $createdAt')
    ..writeln('---')
    ..writeln()
    ..writeln(body);
  return '${buffer.toString().trimRight()}\n';
}

String _nextCommentId({
  required Set<String> blobPaths,
  required String issueRoot,
}) {
  final commentPrefix = _joinPath(issueRoot, 'comments/');
  var maxId = 0;
  for (final path in blobPaths) {
    if (!path.startsWith(commentPrefix) || !path.endsWith('.md')) {
      continue;
    }
    final value = int.tryParse(path.split('/').last.replaceAll('.md', ''));
    if (value != null && value > maxId) {
      maxId = value;
    }
  }
  return (maxId + 1).toString().padLeft(4, '0');
}

String sanitizeAttachmentName(String value) => value
    .replaceAll('\\', '/')
    .split('/')
    .last
    .replaceAll(RegExp(r'[^A-Za-z0-9._-]+'), '-')
    .replaceAll(RegExp(r'-+'), '-')
    .replaceAll(RegExp(r'^-|-$'), '')
    .ifEmpty('attachment.bin');

String _attachmentMetadataPath(String issueRoot) =>
    _joinPath(issueRoot, 'attachments.json');

List<Map<String, Object?>> _attachmentMetadataJson(
  List<IssueAttachment> attachments,
) => [
  for (final attachment in attachments)
    <String, Object?>{
      'id': attachment.id,
      'name': attachment.name,
      'mediaType': attachment.mediaType,
      'sizeBytes': attachment.sizeBytes,
      'author': attachment.author,
      'createdAt': attachment.createdAt,
      'storagePath': attachment.storagePath,
      'revisionOrOid': attachment.revisionOrOid,
      'storageBackend': attachment.storageBackend.persistedValue,
      if (attachment.repositoryPath case final repositoryPath?)
        'repositoryPath': repositoryPath,
      if (attachment.githubReleaseTag case final githubReleaseTag?)
        'githubReleaseTag': githubReleaseTag,
      if (attachment.githubReleaseAssetName case final githubReleaseAssetName?)
        'githubReleaseAssetName': githubReleaseAssetName,
    },
];

IssueAttachment _parseAttachmentMetadataEntry(Map<Object?, Object?> entry) {
  final storageBackend = AttachmentStorageMode.tryParse(
    entry['storageBackend'],
  );
  if (storageBackend == null) {
    throw TrackStateRepositoryException(
      'Attachment metadata entry is missing a valid storageBackend: $entry',
    );
  }
  final id = entry['id']?.toString().trim() ?? '';
  final name = entry['name']?.toString().trim() ?? '';
  final storagePath = entry['storagePath']?.toString().trim() ?? id;
  if (id.isEmpty || name.isEmpty || storagePath.isEmpty) {
    throw TrackStateRepositoryException(
      'Attachment metadata entry must include id, name, and storagePath: $entry',
    );
  }
  final githubReleaseTag = entry['githubReleaseTag']?.toString().trim();
  final githubReleaseAssetName = entry['githubReleaseAssetName']
      ?.toString()
      .trim();
  if (storageBackend == AttachmentStorageMode.githubReleases &&
      ((githubReleaseTag ?? '').isEmpty ||
          (githubReleaseAssetName ?? '').isEmpty)) {
    throw TrackStateRepositoryException(
      'GitHub Releases attachment metadata must include githubReleaseTag and githubReleaseAssetName: $entry',
    );
  }
  return IssueAttachment(
    id: id,
    name: name,
    mediaType:
        entry['mediaType']?.toString().trim().ifEmpty(
          _mediaTypeForPath(name),
        ) ??
        _mediaTypeForPath(name),
    sizeBytes: switch (entry['sizeBytes']) {
      final num value => value.toInt(),
      final String value => int.tryParse(value) ?? 0,
      _ => 0,
    },
    author: entry['author']?.toString() ?? 'unknown',
    createdAt: entry['createdAt']?.toString() ?? 'from repo',
    storagePath: storagePath,
    revisionOrOid: entry['revisionOrOid']?.toString() ?? '',
    storageBackend: storageBackend,
    repositoryPath: (() {
      final value = entry['repositoryPath']?.toString().trim() ?? '';
      return value.isEmpty ? null : value;
    })(),
    githubReleaseTag: (githubReleaseTag == null || githubReleaseTag.isEmpty)
        ? null
        : githubReleaseTag,
    githubReleaseAssetName:
        (githubReleaseAssetName == null || githubReleaseAssetName.isEmpty)
        ? null
        : githubReleaseAssetName,
  );
}

int _sortAttachmentsNewestFirst(IssueAttachment left, IssueAttachment right) {
  final leftCreated = DateTime.tryParse(left.createdAt);
  final rightCreated = DateTime.tryParse(right.createdAt);
  if (leftCreated != null && rightCreated != null) {
    final byTimestamp = rightCreated.compareTo(leftCreated);
    if (byTimestamp != 0) {
      return byTimestamp;
    }
  }
  if (leftCreated != null && rightCreated == null) {
    return -1;
  }
  if (leftCreated == null && rightCreated != null) {
    return 1;
  }
  final byCreatedLabel = right.createdAt.compareTo(left.createdAt);
  if (byCreatedLabel != 0) {
    return byCreatedLabel;
  }
  return left.name.compareTo(right.name);
}

bool _isIssueCommentPath(String path) =>
    path.contains('/comments/') && path.endsWith('.md');

bool _isIssueAttachmentPath(String path) => path.contains('/attachments/');

String _attachmentRevisionOrOid({
  required RepositoryAttachment attachment,
  required bool isLfsTracked,
}) =>
    (isLfsTracked ? attachment.lfsOid : null) ??
    attachment.lfsOid ??
    attachment.revision ??
    '';

String _yamlScalar(String value) {
  final escaped = value.replaceAll('\\', '\\\\').replaceAll('"', '\\"');
  return '"$escaped"';
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

String _issueRoot(String storagePath) =>
    storagePath.substring(0, storagePath.lastIndexOf('/'));

String _archivedIssueStoragePath(String projectRoot, String key) =>
    _joinPath(projectRoot, '.trackstate/archive/$key/main.md');

List<String> _issueArtifactPaths(Set<String> blobPaths, String storagePath) {
  final issueRoot = _issueRoot(storagePath);
  return blobPaths.where((path) {
    if (path == storagePath) {
      return true;
    }
    if (!path.startsWith('$issueRoot/')) {
      return false;
    }
    final relativePath = path.substring(issueRoot.length + 1);
    return !_isNestedIssueArtifactRelativePath(relativePath);
  }).toList()..sort();
}

bool _isNestedIssueArtifactRelativePath(String relativePath) {
  final separatorIndex = relativePath.indexOf('/');
  if (separatorIndex <= 0) {
    return false;
  }
  final firstSegment = relativePath.substring(0, separatorIndex);
  return RegExp(r'^[A-Za-z][A-Za-z0-9]+-\d+$').hasMatch(firstSegment);
}

RepositoryIssueIndexEntry _repositoryIndexEntry(Map entry) {
  final childKeys = entry['children'];
  final labels = entry['labels'];
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
    summary: _nullable(entry['summary']?.toString()),
    issueTypeId: _nullable(entry['issueType']?.toString()),
    statusId: _nullable(entry['status']?.toString()),
    priorityId: _nullable(entry['priority']?.toString()),
    assignee: _nullable(entry['assignee']?.toString()),
    labels: labels is List
        ? labels.map((value) => value.toString()).toList(growable: false)
        : const [],
    updatedLabel: _nullable(entry['updated']?.toString()),
    revision:
        _nullable(entry['revision']?.toString()) ??
        _nullable(entry['sha']?.toString()),
    progress: switch (entry['progress']) {
      final num value => value.toDouble(),
      final String value => double.tryParse(value),
      _ => null,
    },
    resolutionId: _nullable(entry['resolution']?.toString()),
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

List<DeletedIssueTombstone> _dedupeDeletedIssueTombstones(
  List<DeletedIssueTombstone> deleted,
) {
  final byKey = {
    for (final entry in deleted.where((entry) => entry.key.isNotEmpty))
      entry.key: entry,
  };
  final deduped = byKey.values.toList()..sort((a, b) => a.key.compareTo(b.key));
  return deduped;
}

String _tombstoneArtifactPath(String projectRoot, String key) =>
    _joinPath(projectRoot, '.trackstate/tombstones/$key.json');

List<Map<String, Object?>> _repositoryIndexEntriesJson(
  List<RepositoryIssueIndexEntry> entries,
) => [
  for (final entry in entries)
    {
      'key': entry.key,
      'path': entry.path,
      'parent': entry.parentKey,
      'epic': entry.epicKey,
      'parentPath': entry.parentPath,
      'epicPath': entry.epicPath,
      'summary': entry.summary,
      'issueType': entry.issueTypeId,
      'status': entry.statusId,
      'priority': entry.priorityId,
      'assignee': entry.assignee,
      'labels': entry.labels,
      'updated': entry.updatedLabel,
      'revision': entry.revision,
      'progress': entry.progress,
      'resolution': entry.resolutionId,
      'children': entry.childKeys,
      'archived': entry.isArchived,
    },
];

List<Map<String, Object?>> _tombstoneIndexEntriesJson(
  String projectRoot,
  List<DeletedIssueTombstone> deleted,
) => [
  for (final entry in deleted)
    {'key': entry.key, 'path': _tombstoneArtifactPath(projectRoot, entry.key)},
];

Map<String, Object?> _deletedIssueTombstoneJson(DeletedIssueTombstone entry) =>
    {
      'key': entry.key,
      'project': entry.project,
      'formerPath': entry.formerPath,
      'deletedAt': entry.deletedAt,
      if (entry.summary != null) 'summary': entry.summary,
      if (entry.issueTypeId != null) 'issueType': entry.issueTypeId,
      'parent': entry.parentKey,
      'epic': entry.epicKey,
    };

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
        summary: issue.summary,
        issueTypeId: issue.issueTypeId,
        statusId: issue.statusId,
        priorityId: issue.priorityId,
        assignee: _nullable(issue.assignee),
        labels: issue.labels,
        updatedLabel: issue.updatedLabel,
        progress: issue.progress,
        resolutionId: issue.resolutionId,
        revision: null,
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

extension on String {
  String ifEmpty(String fallback) => isEmpty ? fallback : this;
}

const _issueTypeDefinitions = [
  TrackStateConfigEntry(
    id: 'epic',
    name: 'Epic',
    hierarchyLevel: 1,
    icon: 'epic',
    workflowId: 'epic-workflow',
    localizedLabels: {'en': 'Epic'},
  ),
  TrackStateConfigEntry(
    id: 'story',
    name: 'Story',
    hierarchyLevel: 0,
    icon: 'story',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Story'},
  ),
  TrackStateConfigEntry(
    id: 'task',
    name: 'Task',
    hierarchyLevel: 0,
    icon: 'task',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Task'},
  ),
  TrackStateConfigEntry(
    id: 'subtask',
    name: 'Sub-task',
    hierarchyLevel: -1,
    icon: 'subtask',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Sub-task'},
  ),
  TrackStateConfigEntry(
    id: 'bug',
    name: 'Bug',
    hierarchyLevel: 0,
    icon: 'bug',
    workflowId: 'delivery-workflow',
    localizedLabels: {'en': 'Bug'},
  ),
];

const _statusDefinitions = [
  TrackStateConfigEntry(
    id: 'todo',
    name: 'To Do',
    category: 'new',
    localizedLabels: {'en': 'To Do'},
  ),
  TrackStateConfigEntry(
    id: 'in-progress',
    name: 'In Progress',
    category: 'indeterminate',
    localizedLabels: {'en': 'In Progress'},
  ),
  TrackStateConfigEntry(
    id: 'in-review',
    name: 'In Review',
    category: 'indeterminate',
    localizedLabels: {'en': 'In Review'},
  ),
  TrackStateConfigEntry(
    id: 'done',
    name: 'Done',
    category: 'done',
    localizedLabels: {'en': 'Done'},
  ),
];

const _fieldDefinitions = [
  TrackStateFieldDefinition(
    id: 'summary',
    name: 'Summary',
    type: 'string',
    required: true,
    reserved: true,
    localizedLabels: {'en': 'Summary'},
  ),
  TrackStateFieldDefinition(
    id: 'description',
    name: 'Description',
    type: 'markdown',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Description'},
  ),
  TrackStateFieldDefinition(
    id: 'acceptanceCriteria',
    name: 'Acceptance Criteria',
    type: 'markdown',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Acceptance Criteria'},
  ),
  TrackStateFieldDefinition(
    id: 'priority',
    name: 'Priority',
    type: 'option',
    required: false,
    options: _priorityFieldOptions,
    reserved: true,
    localizedLabels: {'en': 'Priority'},
  ),
  TrackStateFieldDefinition(
    id: 'assignee',
    name: 'Assignee',
    type: 'user',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Assignee'},
  ),
  TrackStateFieldDefinition(
    id: 'labels',
    name: 'Labels',
    type: 'array',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Labels'},
  ),
  TrackStateFieldDefinition(
    id: 'storyPoints',
    name: 'Story Points',
    type: 'number',
    required: false,
    reserved: true,
    localizedLabels: {'en': 'Story Points'},
  ),
];

const _priorityFieldOptions = [
  TrackStateFieldOption(id: 'highest', name: 'Highest'),
  TrackStateFieldOption(id: 'high', name: 'High'),
  TrackStateFieldOption(id: 'medium', name: 'Medium'),
  TrackStateFieldOption(id: 'low', name: 'Low'),
];

const _workflowDefinitions = [
  TrackStateWorkflowDefinition(
    id: 'epic-workflow',
    name: 'Epic Workflow',
    statusIds: ['todo', 'in-progress', 'done'],
    transitions: [
      TrackStateWorkflowTransition(
        id: 'epic-start',
        name: 'Start epic',
        fromStatusId: 'todo',
        toStatusId: 'in-progress',
      ),
      TrackStateWorkflowTransition(
        id: 'epic-complete',
        name: 'Complete epic',
        fromStatusId: 'in-progress',
        toStatusId: 'done',
      ),
    ],
  ),
  TrackStateWorkflowDefinition(
    id: 'delivery-workflow',
    name: 'Delivery Workflow',
    statusIds: ['todo', 'in-progress', 'in-review', 'done'],
    transitions: [
      TrackStateWorkflowTransition(
        id: 'start',
        name: 'Start work',
        fromStatusId: 'todo',
        toStatusId: 'in-progress',
      ),
      TrackStateWorkflowTransition(
        id: 'review',
        name: 'Request review',
        fromStatusId: 'in-progress',
        toStatusId: 'in-review',
      ),
      TrackStateWorkflowTransition(
        id: 'complete',
        name: 'Complete',
        fromStatusId: 'in-review',
        toStatusId: 'done',
      ),
      TrackStateWorkflowTransition(
        id: 'reopen',
        name: 'Reopen',
        fromStatusId: 'done',
        toStatusId: 'todo',
      ),
    ],
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
  workflowDefinitions: _workflowDefinitions,
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
          id: 'TRACK/TRACK-1/TRACK-12/attachments/sync-sequence.svg',
          name: 'sync-sequence.svg',
          mediaType: 'image/svg+xml',
          sizeBytes: 5240,
          author: 'ana',
          createdAt: '2026-05-05T00:08:00Z',
          storagePath: 'TRACK/TRACK-1/TRACK-12/attachments/sync-sequence.svg',
          revisionOrOid: 'demo-sync-sequence-revision',
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
