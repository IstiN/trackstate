import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

import '../testing/tests/TS-732/support/ts732_removed_issue_sync_repository.dart';
import '../testing/tests/TS-733/support/ts733_sync_refresh_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'view model clears the selected issue and publishes an info message when a sync refresh removes it from the workspace',
    () async {
      final repository = Ts732RemovedIssueSyncRepository();
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      viewModel.selectIssue(
        viewModel.searchResults.firstWhere(
          (issue) =>
              issue.key == Ts732RemovedIssueSyncRepository.removedIssueKey,
        ),
      );
      await Future<void>.delayed(Duration.zero);

      expect(
        viewModel.selectedIssue?.key,
        Ts732RemovedIssueSyncRepository.removedIssueKey,
      );

      await repository.emitIssueRemovalSync();
      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(
        viewModel.searchResults.map((issue) => issue.key).toList(),
        <String>[Ts732RemovedIssueSyncRepository.remainingIssueKey],
      );
      expect(viewModel.selectedIssue, isNull);
      expect(viewModel.message, isNotNull);
      expect(viewModel.message?.tone, TrackerMessageTone.info);
      expect(
        viewModel.message?.issueKey,
        Ts732RemovedIssueSyncRepository.removedIssueKey,
      );

      viewModel.dispose();
    },
  );

  test(
    'view model clears the selected issue when a sync refresh removes it from active search results',
    () async {
      final repository = Ts733SyncRefreshRepository();
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      await viewModel.updateQuery(Ts733SyncRefreshRepository.query);
      viewModel.selectIssue(
        viewModel.searchResults.firstWhere(
          (issue) => issue.key == Ts733SyncRefreshRepository.issueBKey,
        ),
      );
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.jql, Ts733SyncRefreshRepository.query);
      expect(
        viewModel.selectedIssue?.key,
        Ts733SyncRefreshRepository.issueBKey,
      );

      repository.scheduleIssueBClosure();
      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.jql, Ts733SyncRefreshRepository.query);
      expect(
        viewModel.searchResults.map((issue) => issue.key).toList(),
        <String>[Ts733SyncRefreshRepository.issueAKey],
      );
      expect(viewModel.selectedIssue, isNull);

      viewModel.dispose();
    },
  );

  test(
    'view model queues background refreshes until the edit session ends',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _SyncAwareRepository(snapshot: baseline);
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      await Future<void>.delayed(Duration.zero);

      final selectedIssue = viewModel.selectedIssue!;
      repository.queueHostedRefresh(
        nextSnapshot: TrackerSnapshot(
          project: baseline.project,
          issues: [
            for (final issue in baseline.issues)
              if (issue.key == selectedIssue.key)
                _copyIssue(issue, description: 'Remote description update')
              else
                issue,
          ],
          repositoryIndex: baseline.repositoryIndex,
          loadWarnings: baseline.loadWarnings,
          readiness: baseline.readiness,
          startupRecovery: baseline.startupRecovery,
        ),
        changedPaths: {'${_issueRoot(selectedIssue.storagePath)}/main.md'},
      );

      viewModel.beginEditSession();
      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.hasPendingWorkspaceSyncRefresh, isTrue);
      expect(
        viewModel.selectedIssue?.description,
        isNot('Remote description update'),
      );

      viewModel.endEditSession();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.hasPendingWorkspaceSyncRefresh, isFalse);
      expect(viewModel.selectedIssue?.description, 'Remote description update');
    },
  );

  test(
    'view model defers background refresh while a query update is in flight',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _SyncAwareRepository(snapshot: baseline);
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      repository.delayNextSearchRequest();

      final queryFuture = viewModel.updateQuery(
        'project = TRACK AND status = "In Progress"',
      );
      await Future<void>.delayed(Duration.zero);

      repository.queueHostedRefresh(
        nextSnapshot: TrackerSnapshot(
          project: baseline.project,
          issues: [
            for (final issue in baseline.issues)
              if (issue.key == 'TRACK-12')
                _copyIssue(issue, description: 'Query-safe remote refresh')
              else
                issue,
          ],
          repositoryIndex: baseline.repositoryIndex,
          loadWarnings: baseline.loadWarnings,
          readiness: baseline.readiness,
          startupRecovery: baseline.startupRecovery,
        ),
        changedPaths: {'TRACK-12/main.md'},
      );

      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.hasPendingWorkspaceSyncRefresh, isTrue);

      repository.completePendingSearch();
      await queryFuture;
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.hasPendingWorkspaceSyncRefresh, isFalse);
      expect(viewModel.jql, 'project = TRACK AND status = "In Progress"');
      expect(viewModel.selectedIssue?.description, 'Query-safe remote refresh');
    },
  );

  test(
    'view model applies queued refresh after load more supersedes a pending query request',
    () async {
      final snapshot = _searchPaginationSnapshot();
      final repository = _SyncAwareRepository(snapshot: snapshot);
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      repository.delayNextSearchRequest();

      final queryFuture = viewModel.updateQuery('project = TRACK');
      await Future<void>.delayed(Duration.zero);

      final loadMoreFuture = viewModel.loadMoreSearchResults();
      await Future<void>.delayed(Duration.zero);

      repository.queueHostedRefresh(
        nextSnapshot: TrackerSnapshot(
          project: snapshot.project,
          issues: [
            for (final issue in snapshot.issues)
              if (issue.key == 'TRACK-1')
                _copyIssue(issue, description: 'Refresh survives stale query')
              else
                issue,
          ],
          repositoryIndex: snapshot.repositoryIndex,
          loadWarnings: snapshot.loadWarnings,
          readiness: snapshot.readiness,
          startupRecovery: snapshot.startupRecovery,
        ),
        changedPaths: {'TRACK/TRACK-1/main.md'},
      );

      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.hasPendingWorkspaceSyncRefresh, isTrue);

      repository.completePendingSearch();
      await queryFuture;
      await loadMoreFuture;
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(viewModel.hasPendingWorkspaceSyncRefresh, isFalse);
      expect(viewModel.searchResults.length, 8);
      expect(
        viewModel.selectedIssue?.description,
        'Refresh survives stale query',
      );
    },
  );

  test(
    'view model scopes comment-only hosted refreshes to the selected issue comments',
    () async {
      final baseline = await const DemoTrackStateRepository().loadSnapshot();
      final repository = _ScopedCommentsRefreshRepository(snapshot: baseline);
      final viewModel = TrackerViewModel(repository: repository);

      await viewModel.load();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );
      viewModel.selectIssue(issue);
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);
      repository.resetTracking();

      repository.queueCommentsRefresh(
        issueKey: issue.key,
        updatedCommentBody: 'Scoped sync comment update',
      );

      await viewModel.handleAppResumed();
      await Future<void>.delayed(Duration.zero);
      await Future<void>.delayed(Duration.zero);

      expect(repository.loadSnapshotCalls, 0);
      expect(
        repository.hydrateRequests,
        equals(<Set<IssueHydrationScope>>[
          {IssueHydrationScope.comments},
        ]),
      );
      expect(
        viewModel.selectedIssue?.comments.last.body,
        'Scoped sync comment update',
      );

      viewModel.dispose();
    },
  );
}

class _SyncAwareRepository
    implements TrackStateRepository, WorkspaceSyncRepository {
  _SyncAwareRepository({required TrackerSnapshot snapshot})
    : _snapshot = snapshot;

  TrackerSnapshot _snapshot;
  RepositorySyncState _state = const RepositorySyncState(
    providerType: ProviderType.github,
    repositoryRevision: 'rev-1',
    sessionRevision: 'connected:true:true',
    connectionState: ProviderConnectionState.connected,
  );
  RepositorySyncCheck? _queuedCheck;
  final JqlSearchService _searchService = const JqlSearchService();
  Completer<void>? _delayedSearchCompleter;

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => false;

  void queueHostedRefresh({
    required TrackerSnapshot nextSnapshot,
    required Set<String> changedPaths,
  }) {
    _snapshot = nextSnapshot;
    _state = const RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: 'rev-2',
      sessionRevision: 'connected:true:true',
      connectionState: ProviderConnectionState.connected,
    );
    _queuedCheck = RepositorySyncCheck(
      state: _state,
      signals: const {WorkspaceSyncSignal.hostedRepository},
      changedPaths: changedPaths,
    );
  }

  void delayNextSearchRequest() {
    _delayedSearchCompleter = Completer<void>();
  }

  void completePendingSearch() {
    _delayedSearchCompleter?.complete();
    _delayedSearchCompleter = null;
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    if (previousState == null) {
      return RepositorySyncCheck(state: _state);
    }
    final queuedCheck = _queuedCheck;
    _queuedCheck = null;
    return queuedCheck ?? RepositorySyncCheck(state: _state);
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final delayedSearchCompleter = _delayedSearchCompleter;
    if (delayedSearchCompleter != null) {
      await delayedSearchCompleter.future;
      if (identical(_delayedSearchCompleter, delayedSearchCompleter)) {
        _delayedSearchCompleter = null;
      }
    }
    return _searchService.search(
      issues: _snapshot.issues,
      project: _snapshot.project,
      jql: jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'sync-user', displayName: 'Sync User');

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => throw UnimplementedError();

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => throw UnimplementedError();

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];
}

class _ScopedCommentsRefreshRepository
    extends ProviderBackedTrackStateRepository {
  _ScopedCommentsRefreshRepository({required TrackerSnapshot snapshot})
    : _snapshot = snapshot,
      super(provider: _SyncTestProvider(), supportsGitHubAuth: false);

  TrackerSnapshot _snapshot;
  final JqlSearchService _searchService = const JqlSearchService();
  RepositorySyncState _state = const RepositorySyncState(
    providerType: ProviderType.github,
    repositoryRevision: 'rev-1',
    sessionRevision: 'connected:true:true',
    connectionState: ProviderConnectionState.connected,
  );
  RepositorySyncCheck? _queuedCheck;
  final Map<String, String> _pendingCommentBodies = <String, String>{};
  int loadSnapshotCalls = 0;
  final List<Set<IssueHydrationScope>> hydrateRequests =
      <Set<IssueHydrationScope>>[];

  void resetTracking() {
    loadSnapshotCalls = 0;
    hydrateRequests.clear();
  }

  void queueCommentsRefresh({
    required String issueKey,
    required String updatedCommentBody,
  }) {
    final issue = _snapshot.issues.firstWhere(
      (candidate) => candidate.key == issueKey,
    );
    _pendingCommentBodies[issueKey] = updatedCommentBody;
    _state = const RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: 'rev-2',
      sessionRevision: 'connected:true:true',
      connectionState: ProviderConnectionState.connected,
    );
    _queuedCheck = RepositorySyncCheck(
      state: _state,
      signals: const {WorkspaceSyncSignal.hostedRepository},
      changedPaths: {'${_issueRoot(issue.storagePath)}/comments/0002.md'},
    );
  }

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    if (previousState == null) {
      return RepositorySyncCheck(state: _state);
    }
    final queuedCheck = _queuedCheck;
    _queuedCheck = null;
    return queuedCheck ?? RepositorySyncCheck(state: _state);
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    loadSnapshotCalls += 1;
    return _snapshot;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    return _searchService.search(
      issues: _snapshot.issues,
      project: _snapshot.project,
      jql: jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<TrackStateIssue> hydrateIssue(
    TrackStateIssue issue, {
    Set<IssueHydrationScope> scopes = const {IssueHydrationScope.detail},
    bool force = false,
  }) async {
    hydrateRequests.add(Set<IssueHydrationScope>.from(scopes));
    final currentIssue = _snapshot.issues.firstWhere(
      (candidate) => candidate.key == issue.key,
      orElse: () => issue,
    );
    final pendingCommentBody = _pendingCommentBodies.remove(issue.key);
    final hydratedComments = pendingCommentBody == null
        ? currentIssue.comments
        : <IssueComment>[
            ...currentIssue.comments,
            IssueComment(
              id: '0002',
              author: 'sync-user',
              body: pendingCommentBody,
              updatedLabel: 'now',
              createdAt: '2026-05-14T10:00:00Z',
              updatedAt: '2026-05-14T10:00:00Z',
              storagePath:
                  '${_issueRoot(currentIssue.storagePath)}/comments/0002.md',
            ),
          ];
    final hydrated = currentIssue.copyWith(
      comments: hydratedComments,
      hasDetailLoaded:
          currentIssue.hasDetailLoaded ||
          scopes.contains(IssueHydrationScope.detail),
      hasCommentsLoaded:
          currentIssue.hasCommentsLoaded ||
          scopes.contains(IssueHydrationScope.comments),
      hasAttachmentsLoaded:
          currentIssue.hasAttachmentsLoaded ||
          scopes.contains(IssueHydrationScope.attachments),
    );
    _snapshot = TrackerSnapshot(
      project: _snapshot.project,
      issues: [
        for (final candidate in _snapshot.issues)
          if (candidate.key == hydrated.key) hydrated else candidate,
      ],
      repositoryIndex: _snapshot.repositoryIndex,
      loadWarnings: _snapshot.loadWarnings,
      readiness: _snapshot.readiness,
      startupRecovery: _snapshot.startupRecovery,
    );
    replaceCachedState(snapshot: _snapshot);
    return hydrated;
  }
}

class _SyncTestProvider implements TrackStateProviderAdapter {
  static const RepositoryPermission _permission = RepositoryPermission(
    canRead: true,
    canWrite: true,
    isAdmin: false,
    canCreateBranch: true,
    canManageAttachments: true,
    attachmentUploadMode: AttachmentUploadMode.full,
    supportsReleaseAttachmentWrites: true,
    canCheckCollaborators: false,
  );

  @override
  String get dataRef => 'main';

  @override
  ProviderType get providerType => ProviderType.github;

  @override
  String get repositoryLabel => 'trackstate/trackstate';

  @override
  Future<RepositoryCommitResult> createCommit(
    RepositoryCommitRequest request,
  ) async => RepositoryCommitResult(
    branch: request.branch,
    message: request.message,
    revision: 'sync-test',
  );

  @override
  Future<void> ensureCleanWorktree() async {}

  @override
  Future<RepositoryUser> authenticate(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'sync-user', displayName: 'Sync User');

  @override
  Future<RepositoryBranch> getBranch(String name) async =>
      RepositoryBranch(name: name, exists: true, isCurrent: true);

  @override
  Future<RepositoryPermission> getPermission() async => _permission;

  @override
  Future<bool> isLfsTracked(String path) async => false;

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) async =>
      const <RepositoryTreeEntry>[];

  @override
  Future<RepositoryAttachment> readAttachment(
    String path, {
    required String ref,
  }) async => throw const TrackStateProviderException('Not used in sync test.');

  @override
  Future<RepositoryTextFile> readTextFile(
    String path, {
    required String ref,
  }) async => throw const TrackStateProviderException('Not used in sync test.');

  @override
  Future<String> resolveWriteBranch() async => dataRef;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async => RepositorySyncCheck(
    state: const RepositorySyncState(
      providerType: ProviderType.github,
      repositoryRevision: 'sync-test',
      sessionRevision: 'connected:true:true',
      connectionState: ProviderConnectionState.connected,
      permission: _permission,
    ),
  );

  @override
  Future<RepositoryWriteResult> writeTextFile(
    RepositoryWriteRequest request,
  ) async => RepositoryWriteResult(
    path: request.path,
    branch: request.branch,
    revision: 'sync-test',
  );

  @override
  Future<RepositoryAttachmentWriteResult> writeAttachment(
    RepositoryAttachmentWriteRequest request,
  ) async => throw const TrackStateProviderException('Not used in sync test.');
}

TrackStateIssue _copyIssue(TrackStateIssue issue, {String? description}) {
  return TrackStateIssue(
    key: issue.key,
    project: issue.project,
    issueType: issue.issueType,
    issueTypeId: issue.issueTypeId,
    status: issue.status,
    statusId: issue.statusId,
    priority: issue.priority,
    priorityId: issue.priorityId,
    summary: issue.summary,
    description: description ?? issue.description,
    assignee: issue.assignee,
    reporter: issue.reporter,
    labels: issue.labels,
    components: issue.components,
    fixVersionIds: issue.fixVersionIds,
    watchers: issue.watchers,
    customFields: issue.customFields,
    parentKey: issue.parentKey,
    epicKey: issue.epicKey,
    parentPath: issue.parentPath,
    epicPath: issue.epicPath,
    progress: issue.progress,
    updatedLabel: issue.updatedLabel,
    acceptanceCriteria: issue.acceptanceCriteria,
    comments: issue.comments,
    links: issue.links,
    attachments: issue.attachments,
    isArchived: issue.isArchived,
    hasDetailLoaded: issue.hasDetailLoaded,
    hasCommentsLoaded: issue.hasCommentsLoaded,
    hasAttachmentsLoaded: issue.hasAttachmentsLoaded,
    resolutionId: issue.resolutionId,
    storagePath: issue.storagePath,
    rawMarkdown: issue.rawMarkdown,
  );
}

String _issueRoot(String storagePath) => storagePath.endsWith('/main.md')
    ? storagePath.substring(0, storagePath.length - '/main.md'.length)
    : storagePath;

TrackerSnapshot _searchPaginationSnapshot() {
  final issues = [
    for (var index = 1; index <= 8; index += 1)
      TrackStateIssue(
        key: 'TRACK-$index',
        project: 'TRACK',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.inProgress,
        statusId: 'in-progress',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Paged issue $index',
        description: 'Search result $index',
        assignee: 'user-$index',
        reporter: 'demo-user',
        labels: const ['paged'],
        components: const [],
        fixVersionIds: const [],
        watchers: const [],
        customFields: const {},
        parentKey: null,
        epicKey: null,
        parentPath: null,
        epicPath: null,
        progress: 0,
        updatedLabel: 'just now',
        acceptanceCriteria: const ['Visible in search pagination'],
        comments: const [],
        links: const [],
        attachments: const [],
        isArchived: false,
        hasDetailLoaded: false,
        hasCommentsLoaded: false,
        hasAttachmentsLoaded: false,
        storagePath: 'TRACK/TRACK-$index/main.md',
        rawMarkdown: '',
      ),
  ];
  return TrackerSnapshot(
    project: const ProjectConfig(
      key: 'TRACK',
      name: 'TrackState',
      repository: 'trackstate/trackstate',
      branch: 'main',
      defaultLocale: 'en',
      issueTypeDefinitions: [TrackStateConfigEntry(id: 'story', name: 'Story')],
      statusDefinitions: [
        TrackStateConfigEntry(id: 'in-progress', name: 'In Progress'),
      ],
      fieldDefinitions: [
        TrackStateFieldDefinition(
          id: 'summary',
          name: 'Summary',
          type: 'string',
          required: true,
        ),
      ],
      priorityDefinitions: [
        TrackStateConfigEntry(id: 'medium', name: 'Medium'),
      ],
    ),
    issues: issues,
  );
}
