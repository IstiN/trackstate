import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts773ExplicitLoadSnapshotDeltaRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts773ExplicitLoadSnapshotDeltaRepository()
    : super(snapshot: _initialSnapshot);

  static const int explicitLoadSnapshotDeltaFlag = 1;
  static const String issueAKey = 'TRACK-773-A';
  static const String issueBKey = 'TRACK-773-B';
  static const String issueASummary =
      'Issue-A stays visible while the global reload runs';
  static const String issueBSummary =
      'Issue-B updates through the explicit global reload';
  static const String issueAPath = 'TRACK-773-A/main.md';
  static const String issueBPath = 'TRACK-773-B/main.md';
  static const String openStatusId = 'open';
  static const String closedStatusId = 'closed';
  static const String query = 'status = Open';
  static const String initialIssueBDescription =
      'Initial detail text before the explicit load_snapshot_delta sync runs.';
  static const String updatedIssueBDescription =
      'Updated detail text after the explicit load_snapshot_delta sync forces a full snapshot reload.';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts773-user',
    displayName: 'TS-773 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingExplicitGlobalReload = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;
  int _loadSnapshotCalls = 0;
  int? _scheduledLoadSnapshotDeltaFlag;
  int? _processedLoadSnapshotDeltaFlag;

  int get loadSnapshotCalls => _loadSnapshotCalls;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts773-revision-$_revisionSerial';

  int? get scheduledLoadSnapshotDeltaFlag => _scheduledLoadSnapshotDeltaFlag;

  int? get processedLoadSnapshotDeltaFlag => _processedLoadSnapshotDeltaFlag;

  void scheduleExplicitLoadSnapshotDeltaRefresh() {
    _currentSnapshot = _snapshotWithUpdatedIssueB(_currentSnapshot);
    _pendingExplicitGlobalReload = true;
    _scheduledLoadSnapshotDeltaFlag = explicitLoadSnapshotDeltaFlag;
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
    if (_pendingExplicitGlobalReload) {
      _pendingExplicitGlobalReload = false;
      _revisionSerial += 1;
      _processedLoadSnapshotDeltaFlag = _scheduledLoadSnapshotDeltaFlag;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts773-session',
          connectionState: ProviderConnectionState.connected,
        ),
        signals: const <WorkspaceSyncSignal>{
          WorkspaceSyncSignal.hostedRepository,
        },
        changedPaths: const <String>{},
      );
    }
    return RepositorySyncCheck(
      state: RepositorySyncState(
        providerType: ProviderType.github,
        repositoryRevision: repositoryRevision,
        sessionRevision: 'ts773-session',
        connectionState: ProviderConnectionState.connected,
      ),
    );
  }
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
        id: Ts773ExplicitLoadSnapshotDeltaRepository.openStatusId,
        name: 'Open',
        localizedLabels: <String, String>{'en': 'Open'},
        category: 'new',
      ),
      TrackStateConfigEntry(
        id: Ts773ExplicitLoadSnapshotDeltaRepository.closedStatusId,
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
      key: Ts773ExplicitLoadSnapshotDeltaRepository.issueAKey,
      summary: Ts773ExplicitLoadSnapshotDeltaRepository.issueASummary,
      storagePath: Ts773ExplicitLoadSnapshotDeltaRepository.issueAPath,
      description:
          'Issue-A stays Open so the active query remains visibly populated before and after the global reload.',
      updatedLabel: '1 minute ago',
    ),
    _issue(
      key: Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
      summary: Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
      storagePath: Ts773ExplicitLoadSnapshotDeltaRepository.issueBPath,
      description:
          Ts773ExplicitLoadSnapshotDeltaRepository.initialIssueBDescription,
      updatedLabel: 'just now',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts773ExplicitLoadSnapshotDeltaRepository.issueAKey,
        path: Ts773ExplicitLoadSnapshotDeltaRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts773ExplicitLoadSnapshotDeltaRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts773ExplicitLoadSnapshotDeltaRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: '1 minute ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey,
        path: Ts773ExplicitLoadSnapshotDeltaRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts773ExplicitLoadSnapshotDeltaRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts773ExplicitLoadSnapshotDeltaRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: 'just now',
      ),
    ],
  ),
);

TrackerSnapshot _snapshotWithUpdatedIssueB(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      for (final issue in snapshot.issues)
        if (issue.key == Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey)
          issue.copyWith(
            description: Ts773ExplicitLoadSnapshotDeltaRepository
                .updatedIssueBDescription,
            updatedLabel: 'moments ago',
          )
        else
          issue,
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        for (final entry in snapshot.repositoryIndex.entries)
          if (entry.key == Ts773ExplicitLoadSnapshotDeltaRepository.issueBKey)
            entry.copyWith(updatedLabel: 'moments ago')
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
    statusId: Ts773ExplicitLoadSnapshotDeltaRepository.openStatusId,
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
      'Allow an explicit global snapshot reload request during background sync.',
      'Refresh the selected issue detail from the reloaded snapshot.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# $summary',
  );
}
