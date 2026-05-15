import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts747IdenticalIssueSelectionRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts747IdenticalIssueSelectionRepository() : super(snapshot: _initialSnapshot);

  static const String issueAKey = 'TRACK-747-A';
  static const String issueBKey = 'TRACK-747-B';
  static const String issueSummary =
      'Identical refresh candidate keeps the same visible content';
  static const String issueDescription =
      'Both issues intentionally share the same summary, status, and description so selection must follow the stable issue identity.';
  static const String issueAPath = 'TRACK-747-A/main.md';
  static const String issueBPath = 'TRACK-747-B/main.md';
  static const String openStatusId = 'open';
  static const String query = 'status = Open';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts747-user',
    displayName: 'TS-747 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingRefresh = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts747-revision-$_revisionSerial';

  void scheduleIdenticalIssueRefresh() {
    _currentSnapshot = _recreatedSnapshot(_currentSnapshot);
    _pendingRefresh = true;
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
    if (_pendingRefresh) {
      _pendingRefresh = false;
      _revisionSerial += 1;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts747-session',
          connectionState: ProviderConnectionState.connected,
        ),
        signals: const <WorkspaceSyncSignal>{
          WorkspaceSyncSignal.hostedRepository,
        },
        changedPaths: const <String>{
          issueAPath,
          issueBPath,
          '.trackstate/index/issues.json',
        },
      );
    }
    return RepositorySyncCheck(
      state: RepositorySyncState(
        providerType: ProviderType.github,
        repositoryRevision: repositoryRevision,
        sessionRevision: 'ts747-session',
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
        id: Ts747IdenticalIssueSelectionRepository.openStatusId,
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
        id: 'medium',
        name: 'Medium',
        localizedLabels: <String, String>{'en': 'Medium'},
      ),
    ],
  ),
  issues: <TrackStateIssue>[
    _issue(
      key: Ts747IdenticalIssueSelectionRepository.issueAKey,
      storagePath: Ts747IdenticalIssueSelectionRepository.issueAPath,
    ),
    _issue(
      key: Ts747IdenticalIssueSelectionRepository.issueBKey,
      storagePath: Ts747IdenticalIssueSelectionRepository.issueBPath,
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      _indexEntry(
        key: Ts747IdenticalIssueSelectionRepository.issueAKey,
        path: Ts747IdenticalIssueSelectionRepository.issueAPath,
      ),
      _indexEntry(
        key: Ts747IdenticalIssueSelectionRepository.issueBKey,
        path: Ts747IdenticalIssueSelectionRepository.issueBPath,
      ),
    ],
  ),
);

TrackerSnapshot _recreatedSnapshot(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      _issue(
        key: Ts747IdenticalIssueSelectionRepository.issueBKey,
        storagePath: Ts747IdenticalIssueSelectionRepository.issueBPath,
      ),
      _issue(
        key: Ts747IdenticalIssueSelectionRepository.issueAKey,
        storagePath: Ts747IdenticalIssueSelectionRepository.issueAPath,
      ),
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        _indexEntry(
          key: Ts747IdenticalIssueSelectionRepository.issueBKey,
          path: Ts747IdenticalIssueSelectionRepository.issueBPath,
        ),
        _indexEntry(
          key: Ts747IdenticalIssueSelectionRepository.issueAKey,
          path: Ts747IdenticalIssueSelectionRepository.issueAPath,
        ),
      ],
      deleted: snapshot.repositoryIndex.deleted,
    ),
    loadWarnings: snapshot.loadWarnings,
    readiness: snapshot.readiness,
    startupRecovery: snapshot.startupRecovery,
  );
}

TrackStateIssue _issue({required String key, required String storagePath}) {
  return TrackStateIssue(
    key: key,
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: IssueStatus.todo,
    statusId: Ts747IdenticalIssueSelectionRepository.openStatusId,
    priority: IssuePriority.medium,
    priorityId: 'medium',
    summary: Ts747IdenticalIssueSelectionRepository.issueSummary,
    description: Ts747IdenticalIssueSelectionRepository.issueDescription,
    assignee: 'qa-user',
    reporter: 'qa-user',
    labels: const <String>['search', 'identical'],
    components: const <String>[],
    fixVersionIds: const <String>[],
    watchers: const <String>[],
    customFields: const <String, Object?>{},
    parentKey: null,
    epicKey: null,
    parentPath: null,
    epicPath: null,
    progress: 0,
    updatedLabel: 'just now',
    acceptanceCriteria: const <String>[
      'Selection follows the same stable issue identity across refreshes.',
      'A different issue with identical visible fields must remain unselected.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# ${Ts747IdenticalIssueSelectionRepository.issueSummary}',
  );
}

RepositoryIssueIndexEntry _indexEntry({
  required String key,
  required String path,
}) {
  return RepositoryIssueIndexEntry(
    key: key,
    path: path,
    childKeys: const <String>[],
    summary: Ts747IdenticalIssueSelectionRepository.issueSummary,
    issueTypeId: 'story',
    statusId: Ts747IdenticalIssueSelectionRepository.openStatusId,
    priorityId: 'medium',
    assignee: 'qa-user',
    labels: const <String>['search', 'identical'],
    updatedLabel: 'just now',
  );
}
