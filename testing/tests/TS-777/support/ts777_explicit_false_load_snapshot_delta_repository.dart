import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts777ExplicitFalseLoadSnapshotDeltaRepository
    extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts777ExplicitFalseLoadSnapshotDeltaRepository()
    : super(snapshot: _initialSnapshot);

  static const int explicitLoadSnapshotDeltaValue = 0;
  static const String issueAKey = 'TRACK-777-A';
  static const String issueBKey = 'TRACK-777-B';
  static const String issueASummary =
      'Issue-A keeps the search result list populated during sync checks';
  static const String issueBSummary =
      'Issue-B should not globally reload when load_snapshot_delta=0';
  static const String issueAPath = 'TRACK-777-A/main.md';
  static const String issueBPath = 'TRACK-777-B/main.md';
  static const String openStatusId = 'open';
  static const String closedStatusId = 'closed';
  static const String query = 'status = Open';
  static const String initialIssueBDescription =
      'Initial detail text before any hosted sync comparison runs.';
  static const String controlWithoutFlagDescription =
      'Issue-B changed after a hosted sync without any explicit load_snapshot_delta marker.';
  static const String explicitFalseAttemptDescription =
      'Issue-B changed after the test requested load_snapshot_delta=0, but the visible detail should remain unchanged because the explicit false request must bypass the global reload.';
  static const String contractShapeDescription =
      'RepositorySyncCheck(state, signals, changedPaths)';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts777-user',
    displayName: 'TS-777 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  _PendingTs777Sync? _pendingSync;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;
  int _loadSnapshotCalls = 0;
  int? _lastRequestedLoadSnapshotDelta;
  Set<WorkspaceSyncSignal> _lastReturnedSignals = const <WorkspaceSyncSignal>{};
  Set<String> _lastReturnedChangedPaths = const <String>{};

  int get loadSnapshotCalls => _loadSnapshotCalls;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts777-revision-$_revisionSerial';

  int? get lastRequestedLoadSnapshotDelta => _lastRequestedLoadSnapshotDelta;

  Set<WorkspaceSyncSignal> get lastReturnedSignals => _lastReturnedSignals;

  Set<String> get lastReturnedChangedPaths => _lastReturnedChangedPaths;

  void scheduleHostedSyncWithoutExplicitFlag() {
    _currentSnapshot = _snapshotWithUpdatedIssueB(
      snapshot: _currentSnapshot,
      description: controlWithoutFlagDescription,
      updatedLabel: 'control refresh',
    );
    _pendingSync = const _PendingTs777Sync();
  }

  void scheduleExplicitFalseLoadSnapshotDeltaAttempt() {
    _currentSnapshot = _snapshotWithUpdatedIssueB(
      snapshot: _currentSnapshot,
      description: explicitFalseAttemptDescription,
      updatedLabel: 'explicit false request',
    );
    _pendingSync = const _PendingTs777Sync(
      requestedLoadSnapshotDelta: explicitLoadSnapshotDeltaValue,
    );
  }

  String describeLastRequestedPayload() {
    final requested = _lastRequestedLoadSnapshotDelta;
    return 'requested_load_snapshot_delta=${requested == null ? '<absent>' : requested}';
  }

  String describeLastExposedPayload() {
    return 'signals=${_formatSignals(lastReturnedSignals)}; '
        'changed_paths=${_formatPaths(lastReturnedChangedPaths)}';
  }

  String describeLastPayload() {
    return '${describeLastRequestedPayload()}; ${describeLastExposedPayload()}';
  }

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      _connectedUser;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    _loadSnapshotCalls += 1;
    return _currentSnapshot;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => _searchService.search(
    issues: _currentSnapshot.issues,
    project: _currentSnapshot.project,
    jql: jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    _syncCheckCount += 1;
    final pendingSync = _pendingSync;
    if (pendingSync == null) {
      _lastRequestedLoadSnapshotDelta = null;
      _lastReturnedSignals = const <WorkspaceSyncSignal>{};
      _lastReturnedChangedPaths = const <String>{};
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts777-session',
          connectionState: ProviderConnectionState.connected,
        ),
      );
    }

    _pendingSync = null;
    _revisionSerial += 1;
    _lastRequestedLoadSnapshotDelta = pendingSync.requestedLoadSnapshotDelta;
    _lastReturnedSignals = const <WorkspaceSyncSignal>{
      WorkspaceSyncSignal.hostedRepository,
    };
    _lastReturnedChangedPaths = const <String>{};
    return RepositorySyncCheck(
      state: RepositorySyncState(
        providerType: ProviderType.github,
        repositoryRevision: repositoryRevision,
        sessionRevision: 'ts777-session',
        connectionState: ProviderConnectionState.connected,
      ),
      signals: _lastReturnedSignals,
      changedPaths: _lastReturnedChangedPaths,
    );
  }
}

class _PendingTs777Sync {
  const _PendingTs777Sync({this.requestedLoadSnapshotDelta});

  final int? requestedLoadSnapshotDelta;
}

final TrackerSnapshot _initialSnapshot = TrackerSnapshot(
  project: ProjectConfig(
    key: 'TRACK',
    name: 'TrackState.AI',
    repository: 'trackstate/trackstate',
    branch: 'main',
    defaultLocale: 'en',
    issueTypeDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'story',
        name: 'Story',
        localizedLabels: <String, String>{'en': 'Story'},
        hierarchyLevel: 0,
        icon: 'story',
      ),
    ],
    statusDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: Ts777ExplicitFalseLoadSnapshotDeltaRepository.openStatusId,
        name: 'Open',
        localizedLabels: <String, String>{'en': 'Open'},
        category: 'new',
      ),
      TrackStateConfigEntry(
        id: Ts777ExplicitFalseLoadSnapshotDeltaRepository.closedStatusId,
        name: 'Closed',
        localizedLabels: <String, String>{'en': 'Closed'},
        category: 'done',
      ),
    ],
    fieldDefinitions: <TrackStateFieldDefinition>[
      TrackStateFieldDefinition(
        id: 'summary',
        name: 'Summary',
        type: 'string',
        required: true,
        localizedLabels: <String, String>{'en': 'Summary'},
      ),
      TrackStateFieldDefinition(
        id: 'description',
        name: 'Description',
        type: 'markdown',
        required: false,
        localizedLabels: <String, String>{'en': 'Description'},
      ),
      TrackStateFieldDefinition(
        id: 'priority',
        name: 'Priority',
        type: 'option',
        required: false,
        localizedLabels: <String, String>{'en': 'Priority'},
      ),
      TrackStateFieldDefinition(
        id: 'assignee',
        name: 'Assignee',
        type: 'user',
        required: false,
        localizedLabels: <String, String>{'en': 'Assignee'},
      ),
      TrackStateFieldDefinition(
        id: 'labels',
        name: 'Labels',
        type: 'array',
        required: false,
        localizedLabels: <String, String>{'en': 'Labels'},
      ),
    ],
    priorityDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'medium',
        name: 'Medium',
        localizedLabels: <String, String>{'en': 'Medium'},
      ),
    ],
  ),
  issues: <TrackStateIssue>[
    _issue(
      key: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueAKey,
      summary: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueASummary,
      storagePath: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueAPath,
      description:
          'Issue-A stays Open so the active JQL Search query remains visibly populated before and after the hosted sync comparison.',
      updatedLabel: '1 minute ago',
    ),
    _issue(
      key: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
      summary: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBSummary,
      storagePath: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBPath,
      description: Ts777ExplicitFalseLoadSnapshotDeltaRepository
          .initialIssueBDescription,
      updatedLabel: 'just now',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueAKey,
        path: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts777ExplicitFalseLoadSnapshotDeltaRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: '1 minute ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey,
        path: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts777ExplicitFalseLoadSnapshotDeltaRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: 'just now',
      ),
    ],
  ),
);

TrackerSnapshot _snapshotWithUpdatedIssueB({
  required TrackerSnapshot snapshot,
  required String description,
  required String updatedLabel,
}) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      for (final issue in snapshot.issues)
        if (issue.key ==
            Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey)
          issue.copyWith(description: description, updatedLabel: updatedLabel)
        else
          issue,
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        for (final entry in snapshot.repositoryIndex.entries)
          if (entry.key ==
              Ts777ExplicitFalseLoadSnapshotDeltaRepository.issueBKey)
            entry.copyWith(updatedLabel: updatedLabel)
          else
            entry,
      ],
      deleted: snapshot.repositoryIndex.deleted,
    ),
    loadWarnings: snapshot.loadWarnings,
    readiness: snapshot.readiness,
    startupRecovery: snapshot.startupRecovery,
  );
}

TrackStateIssue _issue({
  required String key,
  required String summary,
  required String storagePath,
  required String description,
  required String updatedLabel,
}) {
  return TrackStateIssue(
    key: key,
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: IssueStatus.todo,
    statusId: Ts777ExplicitFalseLoadSnapshotDeltaRepository.openStatusId,
    priority: IssuePriority.medium,
    priorityId: 'medium',
    summary: summary,
    description: description,
    assignee: 'qa-user',
    reporter: 'qa-user',
    labels: const <String>['search'],
    components: const <String>[],
    fixVersionIds: const <String>[],
    watchers: const <String>[],
    customFields: const <String, Object?>{},
    parentKey: null,
    epicKey: null,
    parentPath: null,
    epicPath: null,
    progress: 0,
    updatedLabel: updatedLabel,
    acceptanceCriteria: const <String>[
      'Interpret load_snapshot_delta=0 as an explicit false request.',
      'Expose an app-visible distinction between the explicit false request and the unflagged hosted sync path.',
      'Bypass the global snapshot reload when the explicit false request is processed.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# $summary',
  );
}

String _formatSignals(Set<WorkspaceSyncSignal> signals) {
  if (signals.isEmpty) {
    return '<empty>';
  }
  return signals.map((signal) => signal.name).join('|');
}

String _formatPaths(Set<String> paths) {
  if (paths.isEmpty) {
    return '<empty>';
  }
  return paths.join('|');
}
