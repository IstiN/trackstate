import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts904NonSelectedIssueRemovalRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts904NonSelectedIssueRemovalRepository() : super(snapshot: _initialSnapshot);

  static const String issueAKey = 'TRACK-904-A';
  static const String issueBKey = 'TRACK-904-B';
  static const String issueASummary =
      'Issue-A remains selected after unrelated issue removal';
  static const String issueBSummary =
      'Issue-B disappears after the sync refresh';
  static const String issueAPath = 'TRACK-904-A/main.md';
  static const String issueBPath = 'TRACK-904-B/main.md';
  static const String openStatusId = 'open';
  static const String closedStatusId = 'closed';
  static const String query = 'status = Open';
  static const String issueADescription =
      'Issue-A detail content stays visible because the active selection remains valid.';
  static const String issueBDescription =
      'Issue-B only exists to verify that removing a different row does not clear the current selection.';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts904-user',
    displayName: 'TS-904 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingIssueBRemoval = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts904-revision-$_revisionSerial';

  void scheduleIssueBRemoval() {
    _currentSnapshot = _snapshotWithoutIssueB(_currentSnapshot);
    _pendingIssueBRemoval = true;
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
    if (_pendingIssueBRemoval) {
      _pendingIssueBRemoval = false;
      _revisionSerial += 1;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts904-session',
          connectionState: ProviderConnectionState.connected,
        ),
        signals: const <WorkspaceSyncSignal>{
          WorkspaceSyncSignal.hostedRepository,
        },
        changedPaths: const <String>{
          issueBPath,
          '.trackstate/index/issues.json',
        },
      );
    }
    return RepositorySyncCheck(
      state: RepositorySyncState(
        providerType: ProviderType.github,
        repositoryRevision: repositoryRevision,
        sessionRevision: 'ts904-session',
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
        id: Ts904NonSelectedIssueRemovalRepository.openStatusId,
        name: 'Open',
        localizedLabels: <String, String>{'en': 'Open'},
        category: 'new',
      ),
      TrackStateConfigEntry(
        id: Ts904NonSelectedIssueRemovalRepository.closedStatusId,
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
      key: Ts904NonSelectedIssueRemovalRepository.issueAKey,
      summary: Ts904NonSelectedIssueRemovalRepository.issueASummary,
      storagePath: Ts904NonSelectedIssueRemovalRepository.issueAPath,
      description: Ts904NonSelectedIssueRemovalRepository.issueADescription,
      updatedLabel: 'just now',
    ),
    _issue(
      key: Ts904NonSelectedIssueRemovalRepository.issueBKey,
      summary: Ts904NonSelectedIssueRemovalRepository.issueBSummary,
      storagePath: Ts904NonSelectedIssueRemovalRepository.issueBPath,
      description: Ts904NonSelectedIssueRemovalRepository.issueBDescription,
      updatedLabel: '1 minute ago',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts904NonSelectedIssueRemovalRepository.issueAKey,
        path: Ts904NonSelectedIssueRemovalRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts904NonSelectedIssueRemovalRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts904NonSelectedIssueRemovalRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: 'just now',
      ),
      RepositoryIssueIndexEntry(
        key: Ts904NonSelectedIssueRemovalRepository.issueBKey,
        path: Ts904NonSelectedIssueRemovalRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts904NonSelectedIssueRemovalRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts904NonSelectedIssueRemovalRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: '1 minute ago',
      ),
    ],
  ),
);

TrackerSnapshot _snapshotWithoutIssueB(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      for (final issue in snapshot.issues)
        if (issue.key != Ts904NonSelectedIssueRemovalRepository.issueBKey)
          issue,
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        for (final entry in snapshot.repositoryIndex.entries)
          if (entry.key != Ts904NonSelectedIssueRemovalRepository.issueBKey)
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
    statusId: Ts904NonSelectedIssueRemovalRepository.openStatusId,
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
      'Keep the active selection when a different issue disappears.',
      'Do not show the unavailable banner when the selected issue still exists.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# $summary',
  );
}
