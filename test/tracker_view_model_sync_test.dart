import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

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
