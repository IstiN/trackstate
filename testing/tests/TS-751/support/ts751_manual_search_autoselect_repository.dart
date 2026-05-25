import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts751ManualSearchAutoselectRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts751ManualSearchAutoselectRepository() : super(snapshot: _initialSnapshot);

  static const String issueAKey = 'TRACK-751-A';
  static const String issueBKey = 'TRACK-751-B';
  static const String issueCKey = 'TRACK-751-C';

  static const String issueASummary =
      'Highest-priority row starts selected before manual search';
  static const String issueBSummary =
      'First high-priority manual search result should auto-select';
  static const String issueCSummary =
      'Second high-priority manual search result remains unselected';

  static const String issueAPath = 'TRACK-751-A/main.md';
  static const String issueBPath = 'TRACK-751-B/main.md';
  static const String issueCPath = 'TRACK-751-C/main.md';

  static const String openStatusId = 'open';
  static const String manualQuery = 'priority = High ORDER BY key ASC';
  static const String unavailableMessageFragment = 'no longer available';

  static const String issueADescription =
      'This highest-priority issue is removed by the linked sync refresh setup.';
  static const String issueBDescription =
      'Manual search should automatically open this first matching issue.';
  static const String issueCDescription =
      'This second matching issue should stay visible but not selected.';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts751-user',
    displayName: 'TS-751 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingRemovalRefresh = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts751-revision-$_revisionSerial';

  void scheduleSelectedIssueRemovalRefresh() {
    _currentSnapshot = _snapshotWithoutIssueA(_currentSnapshot);
    _pendingRemovalRefresh = true;
  }

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      _connectedUser;

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _currentSnapshot;

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
    if (_pendingRemovalRefresh) {
      _pendingRemovalRefresh = false;
      _revisionSerial += 1;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts751-session',
          connectionState: ProviderConnectionState.connected,
        ),
        signals: const <WorkspaceSyncSignal>{
          WorkspaceSyncSignal.hostedRepository,
        },
        changedPaths: const <String>{
          issueAPath,
          '.trackstate/index/issues.json',
        },
      );
    }

    return RepositorySyncCheck(
      state: RepositorySyncState(
        providerType: ProviderType.github,
        repositoryRevision: repositoryRevision,
        sessionRevision: 'ts751-session',
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
        id: Ts751ManualSearchAutoselectRepository.openStatusId,
        name: 'Open',
        localizedLabels: <String, String>{'en': 'Open'},
        category: 'new',
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
        id: 'high',
        name: 'High',
        localizedLabels: <String, String>{'en': 'High'},
      ),
      TrackStateConfigEntry(
        id: 'highest',
        name: 'Highest',
        localizedLabels: <String, String>{'en': 'Highest'},
      ),
    ],
  ),
  issues: <TrackStateIssue>[
    _issue(
      key: Ts751ManualSearchAutoselectRepository.issueAKey,
      summary: Ts751ManualSearchAutoselectRepository.issueASummary,
      storagePath: Ts751ManualSearchAutoselectRepository.issueAPath,
      priority: IssuePriority.highest,
      priorityId: 'highest',
      description: Ts751ManualSearchAutoselectRepository.issueADescription,
      updatedLabel: 'just now',
    ),
    _issue(
      key: Ts751ManualSearchAutoselectRepository.issueBKey,
      summary: Ts751ManualSearchAutoselectRepository.issueBSummary,
      storagePath: Ts751ManualSearchAutoselectRepository.issueBPath,
      priority: IssuePriority.high,
      priorityId: 'high',
      description: Ts751ManualSearchAutoselectRepository.issueBDescription,
      updatedLabel: '2 minutes ago',
    ),
    _issue(
      key: Ts751ManualSearchAutoselectRepository.issueCKey,
      summary: Ts751ManualSearchAutoselectRepository.issueCSummary,
      storagePath: Ts751ManualSearchAutoselectRepository.issueCPath,
      priority: IssuePriority.high,
      priorityId: 'high',
      description: Ts751ManualSearchAutoselectRepository.issueCDescription,
      updatedLabel: '3 minutes ago',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts751ManualSearchAutoselectRepository.issueAKey,
        path: Ts751ManualSearchAutoselectRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts751ManualSearchAutoselectRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts751ManualSearchAutoselectRepository.openStatusId,
        priorityId: 'highest',
        assignee: 'qa-user',
        labels: const <String>['manual-search'],
        updatedLabel: 'just now',
      ),
      RepositoryIssueIndexEntry(
        key: Ts751ManualSearchAutoselectRepository.issueBKey,
        path: Ts751ManualSearchAutoselectRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts751ManualSearchAutoselectRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts751ManualSearchAutoselectRepository.openStatusId,
        priorityId: 'high',
        assignee: 'qa-user',
        labels: const <String>['manual-search'],
        updatedLabel: '2 minutes ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts751ManualSearchAutoselectRepository.issueCKey,
        path: Ts751ManualSearchAutoselectRepository.issueCPath,
        childKeys: <String>[],
        summary: Ts751ManualSearchAutoselectRepository.issueCSummary,
        issueTypeId: 'story',
        statusId: Ts751ManualSearchAutoselectRepository.openStatusId,
        priorityId: 'high',
        assignee: 'qa-user',
        labels: const <String>['manual-search'],
        updatedLabel: '3 minutes ago',
      ),
    ],
  ),
);

TrackerSnapshot _snapshotWithoutIssueA(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      for (final issue in snapshot.issues)
        if (issue.key != Ts751ManualSearchAutoselectRepository.issueAKey) issue,
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        for (final entry in snapshot.repositoryIndex.entries)
          if (entry.key != Ts751ManualSearchAutoselectRepository.issueAKey)
            entry,
      ],
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
  required IssuePriority priority,
  required String priorityId,
  required String description,
  required String updatedLabel,
}) {
  return TrackStateIssue(
    key: key,
    summary: summary,
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: IssueStatus.todo,
    statusId: Ts751ManualSearchAutoselectRepository.openStatusId,
    priority: priority,
    priorityId: priorityId,
    description: description,
    assignee: 'qa-user',
    reporter: 'qa-user',
    labels: const <String>['manual-search'],
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
      'Manual searches should auto-select the first matching row.',
      'Background sync refreshes must not auto-select another issue when the previous one disappears.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    hasDetailLoaded: true,
    rawMarkdown: '# $summary',
  );
}
