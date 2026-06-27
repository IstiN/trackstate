import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../domain/models/trackstate_models.dart';
import '../providers/github/github_trackstate_provider.dart';
import '../providers/trackstate_provider.dart';
import '../services/issue_link_validation_service.dart';
import '../services/project_settings_validation_service.dart';
import '../services/jql_search_service.dart';

part 'trackstate_repository_mutations.dart';
part 'trackstate_repository_helpers.dart';

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
    String? sourceName,
  });
  Future<Uint8List> downloadAttachment(IssueAttachment attachment);
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue);
}

abstract interface class ProjectSettingsRepository {
  Future<TrackerSnapshot> saveProjectSettings(ProjectSettingsCatalog settings);
}

const String projectSettingsNoCommitProducedMessage =
    'No Git commit was produced for the project settings save.';

class ProjectMetadataRefresh {
  const ProjectMetadataRefresh({
    required this.project,
    required this.loadWarnings,
  });

  final ProjectConfig project;
  final List<String> loadWarnings;
}

abstract interface class ProjectMetadataRepository {
  Future<ProjectMetadataRefresh> loadProjectMetadata();
}

abstract interface class WorkspaceSyncRepository {
  bool get usesLocalPersistence;
  Future<RepositorySyncCheck> checkSync({RepositorySyncState? previousState});
}

abstract interface class HostedWorkspaceCatalogRepository {
  Future<List<HostedRepositoryReference>> listAccessibleHostedRepositories();
}

enum IssueHydrationScope { detail, comments, attachments }

extension TrackStateRepositoryAttachmentSupport on TrackStateRepository {
  String resolveIssueAttachmentPath(
    TrackStateIssue issue,
    String name, {
    String? sourceName,
  }) {
    final normalizedName = name.trim();
    if (normalizedName.isEmpty) {
      return _joinPath(
        _issueRoot(issue.storagePath),
        'attachments/attachment.bin',
      );
    }
    return _joinPath(
      _issueRoot(issue.storagePath),
      'attachments/${resolveAttachmentStorageName(normalizedName, sourceName: sourceName)}',
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
    with _TrackStateRepositoryMutations
    implements
        TrackStateRepository,
        ProjectSettingsRepository,
        ProjectMetadataRepository,
        WorkspaceSyncRepository,
        HostedWorkspaceCatalogRepository {
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
    this.hostedStartupProbeTimeout = const Duration(seconds: 11),
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

  @override
  TrackStateRepository get _repository => this;

  @override
  final TrackStateProviderAdapter _provider;
  @override
  final http.Client? _githubClient;
  final Duration hostedStartupProbeTimeout;
  final JqlSearchService _searchService;
  final ProjectSettingsValidationService _projectSettingsValidationService =
      const ProjectSettingsValidationService();
  @override
  final bool usesLocalPersistence;
  @override
  final bool supportsGitHubAuth;
  @override
  TrackerSnapshot? _snapshot;
  @override
  @override
  final Set<String> _knownTombstoneKeys = <String>{};
  @override
  final Map<String, DeletedIssueTombstone> _knownTombstonesByKey =
      <String, DeletedIssueTombstone>{};
  @override
  final Map<String, String?> _snapshotArtifactRevisions = <String, String?>{};
  List<RepositoryTreeEntry> _snapshotTree = const <RepositoryTreeEntry>[];
  @override
  Set<String> _snapshotBlobPaths = const <String>{};
  @override
  final ProviderSession _session;
  final Queue<Completer<void>> _pendingDeleteMutations =
      Queue<Completer<void>>();
  bool _deleteMutationInProgress = false;
  TrackerStartupRecovery? _startupRecovery;
  static const String hostedStartupShellFallbackWarningPrefix =
      'Hosted startup deferred repository bootstrap after ';
  DateTime? _hostedStartupProbeDeadline;

  TrackStateProviderAdapter get providerAdapter => _provider;
  ProviderSession? get session => _session;
  TrackerSnapshot? get cachedSnapshot => _snapshot;

  bool usesHostedStartupShellFallback(TrackerSnapshot? snapshot) =>
      snapshot?.loadWarnings.any(
        (warning) =>
            warning.startsWith(hostedStartupShellFallbackWarningPrefix),
      ) ??
      false;

  TrackerSnapshot buildHostedStartupFallbackSnapshot() {
    final currentSnapshot = _snapshot;
    final warning =
        '$hostedStartupShellFallbackWarningPrefix${_formatStartupProbeTimeout(hostedStartupProbeTimeout)}. '
        'TrackState.AI loaded a fallback shell snapshot so the shell can open while repository data keeps loading.';
    if (currentSnapshot != null) {
      final snapshot = TrackerSnapshot(
        project: currentSnapshot.project,
        issues: currentSnapshot.issues,
        repositoryIndex: currentSnapshot.repositoryIndex,
        loadWarnings: [
          ...currentSnapshot.loadWarnings,
          if (!currentSnapshot.loadWarnings.contains(warning)) warning,
        ],
        readiness: currentSnapshot.readiness,
        startupRecovery: currentSnapshot.startupRecovery,
      );
      _snapshot = snapshot;
      return snapshot;
    }
    final workspaceName = _repositoryWorkspaceName(_provider.repositoryLabel);
    final snapshot = TrackerSnapshot(
      project: ProjectConfig(
        key: _deriveFallbackProjectKey(workspaceName),
        name: workspaceName,
        repository: _provider.repositoryLabel,
        branch: _provider.dataRef,
        defaultLocale: 'en',
        supportedLocales: const <String>['en'],
        issueTypeDefinitions: _issueTypeDefinitions,
        statusDefinitions: _statusDefinitions,
        fieldDefinitions: _fieldDefinitions,
        workflowDefinitions: _workflowDefinitions,
        priorityDefinitions: _priorityDefinitions,
        versionDefinitions: _versionDefinitions,
        componentDefinitions: _componentDefinitions,
        resolutionDefinitions: _resolutionDefinitions,
        attachmentStorage: const ProjectAttachmentStorageSettings(),
      ),
      issues: const <TrackStateIssue>[],
      repositoryIndex: const RepositoryIndex(),
      loadWarnings: <String>[warning],
      readiness: const TrackerBootstrapReadiness(
        domainStates: {
          TrackerDataDomain.projectMeta: TrackerLoadState.partial,
          TrackerDataDomain.issueSummaries: TrackerLoadState.partial,
          TrackerDataDomain.repositoryIndex: TrackerLoadState.partial,
          TrackerDataDomain.issueDetails: TrackerLoadState.partial,
        },
        sectionStates: {
          TrackerSectionKey.dashboard: TrackerLoadState.partial,
          TrackerSectionKey.board: TrackerLoadState.partial,
          TrackerSectionKey.search: TrackerLoadState.partial,
          TrackerSectionKey.hierarchy: TrackerLoadState.partial,
          TrackerSectionKey.settings: TrackerLoadState.ready,
        },
      ),
      startupRecovery: _startupRecovery,
    );
    _snapshot = snapshot;
    return snapshot;
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    try {
      final check = await _provider.checkSync(previousState: previousState);
      final permission = check.state.permission;
      if (permission != null) {
        _syncProviderSession(
          connectionState: check.state.connectionState,
          resolvedUserIdentity: _session.resolvedUserIdentity,
          permission: permission,
        );
      }
      return check;
    } on Object {
      _syncProviderSession(
        connectionState: ProviderConnectionState.error,
        resolvedUserIdentity: _session.resolvedUserIdentity,
        permission: _restrictedPermission,
      );
      rethrow;
    }
  }

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

  @override
  Future<void> _acquireDeleteMutationLock() async {
    if (!_deleteMutationInProgress) {
      _deleteMutationInProgress = true;
      return;
    }
    final waiter = Completer<void>();
    _pendingDeleteMutations.addLast(waiter);
    await waiter.future;
  }

  @override
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

  @override
  Future<List<HostedRepositoryReference>>
  listAccessibleHostedRepositories() async {
    final provider = _provider;
    return switch (provider) {
      RepositoryCatalogReader reader => reader.listAccessibleRepositories(),
      _ => const <HostedRepositoryReference>[],
    };
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
    final snapshot = await _runWithHostedStartupProbeDeadline(
      _loadSetupSnapshot,
    );
    _snapshot = snapshot;
    return snapshot;
  }

  @override
  Future<ProjectMetadataRefresh> loadProjectMetadata() async {
    final metadata = await _runWithHostedStartupProbeDeadline(
      _loadSnapshotInputs,
    );
    final currentSnapshot = _snapshot;
    if (currentSnapshot != null) {
      _snapshot = TrackerSnapshot(
        project: metadata.project,
        issues: currentSnapshot.issues,
        repositoryIndex: currentSnapshot.repositoryIndex,
        loadWarnings: metadata.loadWarnings,
        readiness: currentSnapshot.readiness,
        startupRecovery: currentSnapshot.startupRecovery,
      );
    }
    return ProjectMetadataRefresh(
      project: metadata.project,
      loadWarnings: metadata.loadWarnings,
    );
  }

  @override
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

    final shouldLoadAttachments =
        scopes.contains(IssueHydrationScope.attachments) ||
        currentIssue.hasAttachmentsLoaded;
    if (_snapshotTree.isEmpty ||
        _snapshotBlobPaths.isEmpty ||
        shouldLoadAttachments) {
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

    final markdown = !force && currentIssue.rawMarkdown.isNotEmpty
        ? currentIssue.rawMarkdown
        : await _getRepositoryText(currentIssue.storagePath);
    final acceptanceMarkdown = shouldLoadDetail
        ? await _tryReadIssueAcceptance(issueRoot)
        : _acceptanceCriteriaMarkdown(currentIssue.acceptanceCriteria);
    final commentsResult = shouldLoadComments
        ? await _loadComments(
            blobPaths: _snapshotBlobPaths,
            issueRoot: issueRoot,
            existingComments: force
                ? const <IssueComment>[]
                : currentIssue.comments,
          )
        : _CommentHydrationResult(comments: currentIssue.comments);
    final repositoryIndexEntry = currentSnapshot.repositoryIndex.entryForKey(
      currentIssue.key,
    );
    final links = shouldLoadDetail
        ? await _loadLinks(
            blobPaths: _snapshotBlobPaths,
            issueRoot: issueRoot,
            repositoryIndexEntry: repositoryIndexEntry,
          )
        : currentIssue.links;
    final attachments = shouldLoadAttachments
        ? await _loadAttachments(tree: _snapshotTree, issueRoot: issueRoot)
        : currentIssue.attachments;
    final hydratedIssue =
        _parseIssue(
          storagePath: currentIssue.storagePath,
          markdown: markdown,
          acceptanceMarkdown: acceptanceMarkdown,
          comments: commentsResult.comments,
          links: links,
          attachments: attachments,
          repositoryIndexEntry: repositoryIndexEntry,
          issueTypeDefinitions: currentSnapshot.project.issueTypeDefinitions,
          statusDefinitions: currentSnapshot.project.statusDefinitions,
          priorityDefinitions: currentSnapshot.project.priorityDefinitions,
          resolutionDefinitions: currentSnapshot.project.resolutionDefinitions,
        ).copyWith(
          hasDetailLoaded: shouldLoadDetail,
          hasCommentsLoaded: shouldLoadComments && commentsResult.error == null,
          hasAttachmentsLoaded: shouldLoadAttachments,
        );
    _replaceIssueInSnapshot(hydratedIssue);
    if (commentsResult.error != null) {
      throw TrackStatePartialHydrationException(
        message: '${commentsResult.error}',
        partialIssue: hydratedIssue,
        failedScopes: const {IssueHydrationScope.comments},
      );
    }
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
    final blobEntries = (await _provider.listTree(
      ref: writeBranch,
    )).where((entry) => entry.type == 'blob').toList(growable: false);
    final blobPaths = blobEntries.map((entry) => entry.path).toSet();
    final blobRevisions = {
      for (final entry in blobEntries) entry.path: entry.revision,
    };
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
          blobRevisions: blobRevisions,
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
            blobRevisions: blobRevisions,
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
            blobRevisions: blobRevisions,
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
      final commitResult = await mutator.applyFileChanges(
        RepositoryFileChangeRequest(
          branch: writeBranch,
          message: 'Update project settings',
          changes: changes,
        ),
      );
      if (!commitResult.createdCommit) {
        throw const TrackStateRepositoryException(
          projectSettingsNoCommitProducedMessage,
        );
      }
    }
    final refreshedSnapshot = await loadSnapshot();
    _snapshot = refreshedSnapshot;
    return refreshedSnapshot;
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


  Future<TrackerSnapshot> _loadSetupSnapshot() async {
    final metadata = await _loadSnapshotInputs();
    final loadWarnings = metadata.loadWarnings;
    final tree = metadata.tree;
    final blobPaths = metadata.blobPaths;
    final dataRoot = metadata.dataRoot;
    final repositoryIndex = metadata.repositoryIndex;
    final project = metadata.project;
    final hasTrackStateMetadata = metadata.hasTrackStateMetadata;
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
        readiness: _hostedBootstrapReadiness(),
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
                          (hasTrackStateMetadata
                              ? entry.path.startsWith(
                                      dataRoot.isEmpty ? '' : '$dataRoot/',
                                    ) &&
                                    entry.path.endsWith('/main.md')
                              : _looksLikeTrackStateIssuePath(entry.path)),
                    )
                    .map((entry) => entry.path)
                    .toList()
          ..sort();
    if (issuePaths.isEmpty) {
      if (usesLocalPersistence && !hasTrackStateMetadata) {
        return TrackerSnapshot(
          project: project,
          issues: const <TrackStateIssue>[],
          repositoryIndex: repositoryIndex,
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
      final comments = (await _loadComments(
        blobPaths: blobPaths,
        issueRoot: issueRoot,
      )).comments;
      final links = await _loadLinks(
        blobPaths: blobPaths,
        issueRoot: issueRoot,
        repositoryIndexEntry: indexEntriesByPath[path],
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
          issueTypeDefinitions: project.issueTypeDefinitions,
          statusDefinitions: project.statusDefinitions,
          priorityDefinitions: project.priorityDefinitions,
          resolutionDefinitions: project.resolutionDefinitions,
        ),
      );
    }
    final resolvedIssues = _resolveIssueLinks(issues)
      ..sort((a, b) => a.key.compareTo(b.key));

    final normalizedIndex = _normalizeRepositoryIndex(
      repositoryIndex.entries.isEmpty
          ? _deriveRepositoryIndex(resolvedIssues, repositoryIndex.deleted)
          : repositoryIndex,
      resolvedIssues,
    );
    final indexedIssues = [
      for (final issue in resolvedIssues)
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

  Future<_LoadedSnapshotInputs> _loadSnapshotInputs() async {
    final loadWarnings = <String>[];
    List<RepositoryTreeEntry> tree;
    try {
      tree = await _loadHostedStartupProbe<List<RepositoryTreeEntry>>(
        'listTree(${_provider.dataRef})',
        () => _provider.listTree(ref: _provider.dataRef),
      );
    } on _HostedStartupProbeTimeout catch (error) {
      loadWarnings.add(
        _hostedStartupTimeoutWarning(
          error.path,
          fallbackDescription: 'repository tree',
        ),
      );
      _captureHostedStartupRecoveryFromTimeout(error.path);
      tree = const <RepositoryTreeEntry>[];
    }
    _snapshotTree = tree;
    final blobPaths = tree
        .where((entry) => entry.type == 'blob')
        .map((entry) => entry.path)
        .toSet();
    _snapshotBlobPaths = blobPaths;
    final projectPath = blobPaths.firstWhere(
      (path) => path.endsWith('/project.json') || path == 'project.json',
      orElse: () => '',
    );
    if (projectPath.isEmpty) {
      if (!usesLocalPersistence && loadWarnings.isEmpty) {
        throw const TrackStateRepositoryException(
          'project.json was not found in the repository.',
        );
      }
      final workspaceName = _repositoryWorkspaceName(_provider.repositoryLabel);
      return _LoadedSnapshotInputs(
        tree: tree,
        blobPaths: blobPaths,
        dataRoot: '',
        project: ProjectConfig(
          key: _deriveFallbackProjectKey(workspaceName),
          name: workspaceName,
          repository: _provider.repositoryLabel,
          branch: usesLocalPersistence
              ? await _provider.resolveWriteBranch()
              : _provider.dataRef,
          defaultLocale: 'en',
          supportedLocales: const <String>['en'],
          issueTypeDefinitions: _issueTypeDefinitions,
          statusDefinitions: _statusDefinitions,
          fieldDefinitions: _fieldDefinitions,
          workflowDefinitions: _workflowDefinitions,
          priorityDefinitions: _priorityDefinitions,
          versionDefinitions: _versionDefinitions,
          componentDefinitions: _componentDefinitions,
          resolutionDefinitions: _resolutionDefinitions,
        ),
        repositoryIndex: const RepositoryIndex(),
        loadWarnings: loadWarnings,
        hasTrackStateMetadata: false,
      );
    }
    final dataRoot = projectPath.contains('/')
        ? projectPath.substring(0, projectPath.lastIndexOf('/'))
        : '';
    final resolvedBranchFuture = _provider.resolveWriteBranch();
    Map<String, Object?>? projectJson;
    try {
      projectJson = await _loadHostedStartupProbe<Map<String, Object?>>(
        projectPath,
        () async =>
            await _getRepositoryJson(projectPath) as Map<String, Object?>,
      );
    } on _HostedStartupProbeTimeout catch (error) {
      loadWarnings.add(
        _hostedStartupTimeoutWarning(
          error.path,
          fallbackDescription: 'project metadata',
        ),
      );
      _captureHostedStartupRecoveryFromTimeout(error.path);
    } on GitHubRateLimitException catch (error) {
      _captureHostedStartupRecovery(error);
    }
    final configRoot = projectJson == null
        ? _defaultConfigRoot(dataRoot)
        : _resolveConfigRoot(projectJson, dataRoot);
    final defaultLocale = projectJson?['defaultLocale']?.toString() ?? 'en';
    final attachmentStorage = projectJson == null
        ? const ProjectAttachmentStorageSettings()
        : _resolveAttachmentStorage(projectJson);
    final supportedLocales = projectJson == null
        ? const <String>['en']
        : _resolveSupportedLocales(
            projectJson: projectJson,
            blobPaths: blobPaths,
            configRoot: configRoot,
            defaultLocale: defaultLocale,
          );
    final localizedLabels = await _loadLocalizedLabels(
      blobPaths: blobPaths,
      configRoot: configRoot,
      locales: supportedLocales,
      loadWarnings: loadWarnings,
    );
    final issueTypeWarnings = <String>[];
    final statusWarnings = <String>[];
    final fieldWarnings = <String>[];
    final issueTypesFuture = _loadRequiredConfigEntries(
      _joinPath(configRoot, 'issue-types.json'),
      blobPaths: blobPaths,
      localizedLabels: localizedLabels['issueTypes'] ?? const {},
      loadWarnings: issueTypeWarnings,
      warningSubject: 'issue types',
      fallbackEntries: _issueTypeDefinitions,
    );
    final statusesFuture = _loadRequiredConfigEntries(
      _joinPath(configRoot, 'statuses.json'),
      blobPaths: blobPaths,
      localizedLabels: localizedLabels['statuses'] ?? const {},
      loadWarnings: statusWarnings,
      warningSubject: 'statuses',
      fallbackEntries: _statusDefinitions,
    );
    final fieldsFuture = _getFieldDefinitions(
      _joinPath(configRoot, 'fields.json'),
      blobPaths: blobPaths,
      localizedLabels: localizedLabels['fields'] ?? const {},
      loadWarnings: fieldWarnings,
    );
    final prioritiesFuture = _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'priorities.json'),
      localizedLabels: localizedLabels['priorities'] ?? const {},
      loadWarnings: loadWarnings,
      warningSubject: 'priorities',
    );
    final versionsFuture = _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'versions.json'),
      localizedLabels: localizedLabels['versions'] ?? const {},
      loadWarnings: loadWarnings,
      warningSubject: 'versions',
    );
    final componentsFuture = _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'components.json'),
      localizedLabels: localizedLabels['components'] ?? const {},
      loadWarnings: loadWarnings,
      warningSubject: 'components',
    );
    final resolutionsFuture = _loadOptionalConfigEntries(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'resolutions.json'),
      localizedLabels: localizedLabels['resolutions'] ?? const {},
      loadWarnings: loadWarnings,
      warningSubject: 'resolutions',
    );
    final issueTypes = await issueTypesFuture;
    final repositoryIndexFuture = _loadRepositoryIndex(
      blobPaths: blobPaths,
      dataRoot: dataRoot,
      issueTypeDefinitions: issueTypes,
      loadWarnings: loadWarnings,
    );
    final statuses = await statusesFuture;
    final workflowsFuture = _loadWorkflowDefinitions(
      blobPaths: blobPaths,
      path: _joinPath(configRoot, 'workflows.json'),
      statusDefinitions: statuses,
      loadWarnings: loadWarnings,
    );
    final fields = await fieldsFuture;
    final priorities = await prioritiesFuture;
    final versions = await versionsFuture;
    final components = await componentsFuture;
    final resolutions = await resolutionsFuture;
    final workflows = await workflowsFuture;
    final repositoryIndex = await repositoryIndexFuture;
    loadWarnings
      ..addAll(issueTypeWarnings)
      ..addAll(statusWarnings)
      ..addAll(fieldWarnings);
    final project = ProjectConfig(
      key:
          projectJson?['key'] as String? ??
          _deriveFallbackProjectKey(_startupFallbackProjectName(dataRoot)),
      name:
          projectJson?['name'] as String? ??
          _startupFallbackProjectName(dataRoot),
      repository: _provider.repositoryLabel,
      branch: await resolvedBranchFuture,
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
    return _LoadedSnapshotInputs(
      tree: tree,
      blobPaths: blobPaths,
      dataRoot: dataRoot,
      project: project,
      repositoryIndex: repositoryIndex,
      loadWarnings: loadWarnings,
      hasTrackStateMetadata: true,
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

  TrackerBootstrapReadiness _hostedBootstrapReadiness() {
    if (_startupRecovery == null) {
      return const TrackerBootstrapReadiness(
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
      );
    }
    return const TrackerBootstrapReadiness(
      domainStates: {
        TrackerDataDomain.projectMeta: TrackerLoadState.ready,
        TrackerDataDomain.issueSummaries: TrackerLoadState.partial,
        TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
        TrackerDataDomain.issueDetails: TrackerLoadState.loading,
      },
      sectionStates: {
        TrackerSectionKey.dashboard: TrackerLoadState.partial,
        TrackerSectionKey.board: TrackerLoadState.partial,
        TrackerSectionKey.search: TrackerLoadState.partial,
        TrackerSectionKey.hierarchy: TrackerLoadState.partial,
        TrackerSectionKey.settings: TrackerLoadState.ready,
      },
    );
  }

  void _validateHostedBootstrapIndex({
    required RepositoryIndex repositoryIndex,
    required List<String> issuePathsInTree,
  }) {
    if (repositoryIndex.entries.isEmpty) {
      throw const HostedBootstrapIndexValidationException(
        'Hosted bootstrap requires .trackstate/index/issues.json with summary entries. Regenerate the tracker indexes and retry.',
      );
    }
    for (final entry in repositoryIndex.entries) {
      if ((entry.summary ?? '').trim().isEmpty ||
          (entry.issueTypeId ?? '').trim().isEmpty ||
          (entry.statusId ?? '').trim().isEmpty ||
          (entry.updatedLabel ?? '').trim().isEmpty) {
        throw HostedBootstrapIndexValidationException(
          'Hosted bootstrap requires summary metadata for ${entry.key} in .trackstate/index/issues.json. Regenerate the tracker indexes and retry.',
        );
      }
    }
    final indexedPaths =
        repositoryIndex.entries.map((entry) => entry.path).toList()..sort();
    if (indexedPaths.length != issuePathsInTree.length) {
      throw const HostedBootstrapIndexValidationException(
        'Hosted bootstrap index is inconsistent with repository issue paths. Regenerate the tracker indexes and retry.',
      );
    }
    for (var index = 0; index < indexedPaths.length; index += 1) {
      if (indexedPaths[index] != issuePathsInTree[index]) {
        throw const HostedBootstrapIndexValidationException(
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

  String _defaultConfigRoot(String dataRoot) =>
      dataRoot.isEmpty ? 'config' : '$dataRoot/config';

  String _startupFallbackProjectName(String dataRoot) {
    final trimmedRoot = dataRoot.trim();
    if (trimmedRoot.isNotEmpty) {
      final segments = trimmedRoot.split('/');
      return segments.lastWhere((segment) => segment.trim().isNotEmpty);
    }
    return _repositoryWorkspaceName(_provider.repositoryLabel);
  }

  Future<T> _loadHostedStartupProbe<T>(
    String path,
    Future<T> Function() load,
  ) async {
    if (usesLocalPersistence) {
      return load();
    }
    final timeout = _remainingHostedStartupProbeTimeout;
    if (timeout <= Duration.zero) {
      throw _HostedStartupProbeTimeout(path, hostedStartupProbeTimeout);
    }
    return load().timeout(
      timeout,
      onTimeout: () =>
          throw _HostedStartupProbeTimeout(path, hostedStartupProbeTimeout),
    );
  }

  Future<T> _runWithHostedStartupProbeDeadline<T>(
    Future<T> Function() action,
  ) async {
    if (usesLocalPersistence) {
      return action();
    }
    final previousDeadline = _hostedStartupProbeDeadline;
    _hostedStartupProbeDeadline ??= DateTime.now().add(
      hostedStartupProbeTimeout,
    );
    try {
      return await action();
    } finally {
      _hostedStartupProbeDeadline = previousDeadline;
    }
  }

  Duration get _remainingHostedStartupProbeTimeout {
    final deadline = _hostedStartupProbeDeadline;
    if (deadline == null) {
      return hostedStartupProbeTimeout;
    }
    final remaining = deadline.difference(DateTime.now());
    return remaining <= Duration.zero ? Duration.zero : remaining;
  }

  String _hostedStartupTimeoutWarning(
    String path, {
    required String fallbackDescription,
  }) {
    return 'Hosted startup deferred $path after ${_formatStartupProbeTimeout(hostedStartupProbeTimeout)}. '
        'TrackState.AI loaded fallback $fallbackDescription so the shell can open while repository data keeps loading.';
  }

  ProjectAttachmentStorageSettings _resolveAttachmentStorage(
    Map<String, Object?> projectJson,
  ) {
    final rawAttachmentStorage = projectJson['attachmentStorage'];
    if (rawAttachmentStorage == null) {
      return const ProjectAttachmentStorageSettings();
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
    required List<String> loadWarnings,
  }) async {
    final result = <String, Map<String, Map<String, String>>>{};
    for (final locale in locales) {
      final path = _joinPath(configRoot, 'i18n/$locale.json');
      if (!blobPaths.contains(path)) {
        continue;
      }
      Object? json;
      try {
        json = await _loadHostedStartupProbe<Object?>(
          path,
          () => _getRepositoryJson(path),
        );
      } on _HostedStartupProbeTimeout catch (error) {
        loadWarnings.add(
          _hostedStartupTimeoutWarning(
            error.path,
            fallbackDescription: 'localized labels',
          ),
        );
        _captureHostedStartupRecoveryFromTimeout(error.path);
        continue;
      } on GitHubRateLimitException catch (error) {
        _captureHostedStartupRecovery(error);
        continue;
      }
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
      return await _loadHostedStartupProbe<List<TrackStateConfigEntry>>(
        path,
        () => _getConfigEntries(path, localizedLabels: localizedLabels),
      );
    } on FormatException catch (error) {
      loadWarnings.add(
        'Falling back to built-in $warningSubject after failing to parse $path: $error',
      );
      return List<TrackStateConfigEntry>.from(fallbackEntries, growable: false);
    } on _HostedStartupProbeTimeout catch (error) {
      loadWarnings.add(
        _hostedStartupTimeoutWarning(
          error.path,
          fallbackDescription: warningSubject,
        ),
      );
      _captureHostedStartupRecoveryFromTimeout(error.path);
      return List<TrackStateConfigEntry>.from(fallbackEntries, growable: false);
    } on GitHubRateLimitException catch (error) {
      _captureHostedStartupRecovery(error);
      return List<TrackStateConfigEntry>.from(fallbackEntries, growable: false);
    }
  }

  Future<List<TrackStateConfigEntry>> _loadOptionalConfigEntries({
    required Set<String> blobPaths,
    required String path,
    required Map<String, Map<String, String>> localizedLabels,
    required List<String> loadWarnings,
    required String warningSubject,
  }) async {
    if (!blobPaths.contains(path)) return const [];
    try {
      return await _loadHostedStartupProbe<List<TrackStateConfigEntry>>(
        path,
        () => _getConfigEntries(path, localizedLabels: localizedLabels),
      );
    } on _HostedStartupProbeTimeout catch (error) {
      loadWarnings.add(
        _hostedStartupTimeoutWarning(
          error.path,
          fallbackDescription: warningSubject,
        ),
      );
      _captureHostedStartupRecoveryFromTimeout(error.path);
      return const [];
    } on GitHubRateLimitException catch (error) {
      _captureHostedStartupRecovery(error);
      return const [];
    }
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
      final json = await _loadHostedStartupProbe<Object?>(
        path,
        () => _getRepositoryJson(path),
      );
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
    } on _HostedStartupProbeTimeout catch (error) {
      loadWarnings.add(
        _hostedStartupTimeoutWarning(error.path, fallbackDescription: 'fields'),
      );
      _captureHostedStartupRecoveryFromTimeout(error.path);
      return List<TrackStateFieldDefinition>.from(
        _fieldDefinitions,
        growable: false,
      );
    } on GitHubRateLimitException catch (error) {
      _captureHostedStartupRecovery(error);
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
    required List<String> loadWarnings,
  }) async {
    if (!blobPaths.contains(path)) {
      return const [];
    }
    Object? json;
    try {
      json = await _loadHostedStartupProbe<Object?>(
        path,
        () => _getRepositoryJson(path),
      );
    } on _HostedStartupProbeTimeout catch (error) {
      loadWarnings.add(
        _hostedStartupTimeoutWarning(
          error.path,
          fallbackDescription: 'workflows',
        ),
      );
      _captureHostedStartupRecoveryFromTimeout(error.path);
      return const [];
    } on GitHubRateLimitException catch (error) {
      _captureHostedStartupRecovery(error);
      return const [];
    }
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
    required List<String> loadWarnings,
  }) async {
    final issuesPath = _joinPath(dataRoot, '.trackstate/index/issues.json');
    final entries = <RepositoryIssueIndexEntry>[];
    if (blobPaths.contains(issuesPath)) {
      try {
        final json = await _loadHostedStartupProbe<Object?>(
          issuesPath,
          () => _getRepositoryJson(issuesPath),
        );
        if (json is List) {
          entries.addAll(
            json
                .whereType<Map>()
                .map((entry) => _repositoryIndexEntry(entry))
                .where((entry) => blobPaths.contains(entry.path)),
          );
        }
      } on _HostedStartupProbeTimeout catch (error) {
        loadWarnings.add(
          _hostedStartupTimeoutWarning(
            error.path,
            fallbackDescription: 'summary issue index',
          ),
        );
        _captureHostedStartupRecoveryFromTimeout(error.path);
        entries.addAll(
          _fallbackHostedRepositoryIndexEntries(
            blobPaths: blobPaths,
            dataRoot: dataRoot,
          ),
        );
      } on GitHubRateLimitException catch (error) {
        _captureHostedStartupRecovery(error);
        entries.addAll(
          _fallbackHostedRepositoryIndexEntries(
            blobPaths: blobPaths,
            dataRoot: dataRoot,
          ),
        );
      }
    }
    final deleted = await _loadDeletedIssueTombstones(
      blobPaths: blobPaths,
      dataRoot: dataRoot,
      issueTypeDefinitions: issueTypeDefinitions,
      loadWarnings: loadWarnings,
    );
    return RepositoryIndex(entries: entries, deleted: deleted);
  }

  Future<List<DeletedIssueTombstone>> _loadDeletedIssueTombstones({
    required Set<String> blobPaths,
    required String dataRoot,
    required List<TrackStateConfigEntry> issueTypeDefinitions,
    required List<String> loadWarnings,
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
        json = await _loadHostedStartupProbe<Object?>(
          tombstonesPath,
          () => _getRepositoryJson(tombstonesPath),
        );
      } on _HostedStartupProbeTimeout catch (error) {
        loadWarnings.add(
          _hostedStartupTimeoutWarning(
            error.path,
            fallbackDescription: 'deleted issue index',
          ),
        );
        _captureHostedStartupRecoveryFromTimeout(error.path);
        return _dedupeDeletedIssueTombstones(deleted);
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
            tombstoneJson = await _loadHostedStartupProbe<Object?>(
              tombstonePath,
              () => _getRepositoryJson(tombstonePath),
            );
          } on _HostedStartupProbeTimeout catch (error) {
            loadWarnings.add(
              _hostedStartupTimeoutWarning(
                error.path,
                fallbackDescription: 'deleted issue metadata',
              ),
            );
            _captureHostedStartupRecoveryFromTimeout(error.path);
            return _dedupeDeletedIssueTombstones(deleted);
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
        json = await _loadHostedStartupProbe<Object?>(
          deletedPath,
          () => _getRepositoryJson(deletedPath),
        );
      } on _HostedStartupProbeTimeout catch (error) {
        loadWarnings.add(
          _hostedStartupTimeoutWarning(
            error.path,
            fallbackDescription: 'legacy deleted issue index',
          ),
        );
        _captureHostedStartupRecoveryFromTimeout(error.path);
        return _dedupeDeletedIssueTombstones(deleted);
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

  List<RepositoryIssueIndexEntry> _fallbackHostedRepositoryIndexEntries({
    required Set<String> blobPaths,
    required String dataRoot,
  }) {
    final issuePaths =
        blobPaths
            .where(
              (path) =>
                  path.startsWith(dataRoot.isEmpty ? '' : '$dataRoot/') &&
                  path.endsWith('/main.md'),
            )
            .toList()
          ..sort();
    final fallbackEntries = <RepositoryIssueIndexEntry>[];
    for (final path in issuePaths) {
      final segments = path.split('/');
      if (segments.length < 3) {
        continue;
      }
      final issueSegments = segments.sublist(1, segments.length - 1);
      if (issueSegments.isEmpty) {
        continue;
      }
      final key = issueSegments.last;
      final issueRoot = _issueRoot(path);
      final hasChildren = issuePaths.any(
        (candidate) => candidate != path && candidate.startsWith('$issueRoot/'),
      );
      final parentKey = issueSegments.length >= 3
          ? issueSegments[issueSegments.length - 2]
          : null;
      final epicKey = issueSegments.length >= 2 ? issueSegments.first : null;
      final issueTypeId = switch (issueSegments.length) {
        >= 3 => 'subtask',
        _ when hasChildren => 'epic',
        _ => 'story',
      };
      fallbackEntries.add(
        RepositoryIssueIndexEntry(
          key: key,
          path: path,
          parentKey: parentKey,
          epicKey: epicKey == key ? null : epicKey,
          childKeys: const [],
          isArchived: false,
          summary: key,
          issueTypeId: issueTypeId,
          statusId: 'todo',
          priorityId: 'medium',
          labels: const <String>[],
          updatedLabel: 'loading...',
          progress: issueTypeId == 'subtask' ? 0 : .35,
          revision: null,
        ),
      );
    }
    return fallbackEntries;
  }

  void _captureHostedStartupRecovery(GitHubRateLimitException error) {
    _startupRecovery ??= TrackerStartupRecovery(
      kind: TrackerStartupRecoveryKind.githubRateLimit,
      failedPath: error.requestPath,
      retryAfter: error.retryAfter,
    );
  }

  void _captureHostedStartupRecoveryFromTimeout(String failedPath) {
    _startupRecovery ??= TrackerStartupRecovery(
      kind: TrackerStartupRecoveryKind.githubRateLimit,
      failedPath: failedPath,
    );
  }

  Future<_CommentHydrationResult> _loadComments({
    required Set<String> blobPaths,
    required String issueRoot,
    List<IssueComment> existingComments = const <IssueComment>[],
  }) async {
    final commentPrefix = _joinPath(issueRoot, 'comments/');
    final commentPaths =
        blobPaths
            .where(
              (path) => path.startsWith(commentPrefix) && path.endsWith('.md'),
            )
            .toList()
          ..sort();
    final existingByPath = {
      for (final comment in existingComments)
        if (comment.storagePath.isNotEmpty) comment.storagePath: comment,
    };
    final comments = <IssueComment>[];
    Object? firstError;
    for (final path in commentPaths) {
      final existing = existingByPath[path];
      if (existing != null) {
        comments.add(existing);
        continue;
      }
      try {
        comments.add(_parseComment(path, await _getRepositoryText(path)));
      } on Object catch (error) {
        firstError ??= error;
      }
    }
    return _CommentHydrationResult(comments: comments, error: firstError);
  }

  Future<List<IssueLink>> _loadLinks({
    required Set<String> blobPaths,
    required String issueRoot,
    RepositoryIssueIndexEntry? repositoryIndexEntry,
  }) async {
    final linksPath = _joinPath(issueRoot, 'links.json');
    if (!blobPaths.contains(linksPath)) {
      return repositoryIndexEntry?.links ?? const [];
    }
    final json = await _getRepositoryJson(linksPath);
    if (json is! List) return const [];
    return json
        .whereType<Map>()
        .map(_issueLinkFromStoredJsonMap)
        .where((link) => link.targetKey.isNotEmpty)
        .toList(growable: false);
  }

  List<TrackStateIssue> _resolveIssueLinks(List<TrackStateIssue> issues) {
    final inboundByKey = <String, List<IssueLink>>{};
    for (final issue in issues) {
      for (final link in issue.links) {
        final targetKey = link.targetKey.trim();
        if (targetKey.isEmpty) {
          continue;
        }
        inboundByKey
            .putIfAbsent(targetKey, () => <IssueLink>[])
            .add(_inverseIssueLink(link, sourceKey: issue.key));
      }
    }

    return [
      for (final issue in issues)
        issue.copyWith(
          links: _dedupeIssueLinks(<IssueLink>[
            ...issue.links,
            ...?inboundByKey[issue.key],
          ]),
        ),
    ];
  }

  List<IssueLink> _dedupeIssueLinks(List<IssueLink> links) {
    final seen = <String>{};
    final deduped = <IssueLink>[];
    for (final link in links) {
      final signature =
          '${_canonicalConfigId(link.type)}|${link.targetKey}|${_canonicalConfigId(link.direction)}';
      if (seen.add(signature)) {
        deduped.add(link);
      }
    }
    return deduped;
  }

  IssueLink _inverseIssueLink(IssueLink link, {required String sourceKey}) {
    final normalizedType = _canonicalConfigId(link.type);
    final normalizedDirection = _canonicalConfigId(link.direction);
    final invertedDirection = normalizedDirection == 'inward'
        ? 'outward'
        : 'inward';
    final invertedType = switch (normalizedType) {
      'blocks' => invertedDirection == 'inward' ? 'is blocked by' : 'blocks',
      'is-blocked-by' =>
        invertedDirection == 'inward' ? 'is blocked by' : 'blocks',
      'duplicates' =>
        invertedDirection == 'inward' ? 'is duplicated by' : 'duplicates',
      'is-duplicated-by' =>
        invertedDirection == 'inward' ? 'is duplicated by' : 'duplicates',
      'clones' => invertedDirection == 'inward' ? 'is cloned by' : 'clones',
      'is-cloned-by' =>
        invertedDirection == 'inward' ? 'is cloned by' : 'clones',
      'relates' || 'relates-to' => 'relates to',
      _ => link.type,
    };
    return IssueLink(
      type: invertedType,
      targetKey: sourceKey,
      direction: invertedDirection,
    );
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
      RepositoryAttachment? attachment;
      try {
        attachment = await _provider.readAttachment(
          entry.path,
          ref: _provider.dataRef,
        );
      } on TrackStateProviderException catch (error) {
        // Only skip attachments that are genuinely missing (404). Other read
        // errors should still surface as deferred section errors.
        if (error.message.contains('(404):') || error.message.contains('404')) {
          continue;
        }
        rethrow;
      }
      List<RepositoryHistoryCommit> history = const <RepositoryHistoryCommit>[];
      if (historyReader != null) {
        try {
          history = await historyReader.listHistory(
            ref: _provider.dataRef,
            path: entry.path,
            limit: 1,
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

  @override
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

  @override
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

  @override
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

  @override
  Future<String?> _existingRevision({
    required String path,
    required String ref,
    required Set<String> blobPaths,
    Map<String, String?>? blobRevisions,
  }) async {
    if (!blobPaths.contains(path)) {
      return null;
    }
    final revision = blobRevisions?[path];
    if (revision != null || blobRevisions?.containsKey(path) == true) {
      return revision;
    }
    final file = await _provider.readTextFile(path, ref: ref);
    return file.revision;
  }

  @override
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
        if (_isIssueArtifactPath(
          issueStoragePath: issue.storagePath,
          candidatePath: path,
        )) {
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
    super.hostedStartupProbeTimeout = const Duration(seconds: 11),
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
