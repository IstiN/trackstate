import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts742MatchingIssueSyncRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts742MatchingIssueSyncRepository() : super(snapshot: _initialSnapshot);

  static const String issueAKey = 'TRACK-742-A';
  static const String issueBKey = 'TRACK-742-B';
  static const String issueASummary =
      'Issue-A stays visible in the active query';
  static const String issueBSummary =
      'Issue-B remains selected after the refresh';
  static const String issueAPath = 'TRACK-742-A/main.md';
  static const String issueBPath = 'TRACK-742-B/main.md';
  static const String openStatusId = 'open';
  static const String closedStatusId = 'closed';
  static const String query = 'status = Open';
  static const String initialIssueBDescription =
      'Initial detail text before the background sync refresh runs.';
  static const String updatedIssueBDescription =
      'Updated detail text after the background sync refresh while the issue still matches the query.';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts742-user',
    displayName: 'TS-742 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingDescriptionRefresh = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts742-revision-$_revisionSerial';

  void scheduleSelectedIssueDescriptionRefresh() {
    _currentSnapshot = _snapshotWithUpdatedIssueB(_currentSnapshot);
    _pendingDescriptionRefresh = true;
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
    if (_pendingDescriptionRefresh) {
      _pendingDescriptionRefresh = false;
      _revisionSerial += 1;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts742-session',
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
        sessionRevision: 'ts742-session',
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
        id: Ts742MatchingIssueSyncRepository.openStatusId,
        name: 'Open',
        localizedLabels: <String, String>{'en': 'Open'},
        category: 'new',
      ),
      TrackStateConfigEntry(
        id: Ts742MatchingIssueSyncRepository.closedStatusId,
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
      key: Ts742MatchingIssueSyncRepository.issueAKey,
      summary: Ts742MatchingIssueSyncRepository.issueASummary,
      storagePath: Ts742MatchingIssueSyncRepository.issueAPath,
      description:
          'Issue-A stays Open so the search results keep more than one visible row.',
      updatedLabel: '1 minute ago',
    ),
    _issue(
      key: Ts742MatchingIssueSyncRepository.issueBKey,
      summary: Ts742MatchingIssueSyncRepository.issueBSummary,
      storagePath: Ts742MatchingIssueSyncRepository.issueBPath,
      description: Ts742MatchingIssueSyncRepository.initialIssueBDescription,
      updatedLabel: 'just now',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts742MatchingIssueSyncRepository.issueAKey,
        path: Ts742MatchingIssueSyncRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts742MatchingIssueSyncRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts742MatchingIssueSyncRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: '1 minute ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts742MatchingIssueSyncRepository.issueBKey,
        path: Ts742MatchingIssueSyncRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts742MatchingIssueSyncRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts742MatchingIssueSyncRepository.openStatusId,
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
        if (issue.key == Ts742MatchingIssueSyncRepository.issueBKey)
          issue.copyWith(
            description:
                Ts742MatchingIssueSyncRepository.updatedIssueBDescription,
            updatedLabel: 'moments ago',
          )
        else
          issue,
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        for (final entry in snapshot.repositoryIndex.entries)
          if (entry.key == Ts742MatchingIssueSyncRepository.issueBKey)
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
    statusId: Ts742MatchingIssueSyncRepository.openStatusId,
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
      'Keep the active query visible after refresh.',
      'Keep the same selected issue detail open when it still matches the query.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# $summary',
  );
}
