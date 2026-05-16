import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts746ReorderedIssueSyncRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts746ReorderedIssueSyncRepository() : super(snapshot: _initialSnapshot);

  static const String issueAKey = 'TRACK-746-A';
  static const String issueBKey = 'TRACK-746-B';
  static const String issueCKey = 'TRACK-746-C';

  static const String issueASummary =
      'High-priority row becomes the new top result';
  static const String issueBSummary =
      'Selected issue must stay highlighted after reordering';
  static const String issueCSummary =
      'Medium-priority row stays between top and bottom';

  static const String issueAPath = 'TRACK-746-A/main.md';
  static const String issueBPath = 'TRACK-746-B/main.md';
  static const String issueCPath = 'TRACK-746-C/main.md';

  static const String openStatusId = 'open';
  static const String query = 'status = Open ORDER BY priority DESC';

  static const String initialIssueBDescription =
      'Initial detail text before the selected row is reordered by the refresh.';
  static const String updatedIssueBDescription =
      'Updated detail text after the selected row moved to its new sorted position.';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts746-user',
    displayName: 'TS-746 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingReorderRefresh = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts746-revision-$_revisionSerial';

  void scheduleSelectedIssueReorderRefresh() {
    _currentSnapshot = _snapshotWithReorderedSelectedIssue(_currentSnapshot);
    _pendingReorderRefresh = true;
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
    if (_pendingReorderRefresh) {
      _pendingReorderRefresh = false;
      _revisionSerial += 1;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts746-session',
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
        sessionRevision: 'ts746-session',
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
        id: Ts746ReorderedIssueSyncRepository.openStatusId,
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
        id: 'low',
        name: 'Low',
        localizedLabels: <String, String>{'en': 'Low'},
      ),
      TrackStateConfigEntry(
        id: 'medium',
        name: 'Medium',
        localizedLabels: <String, String>{'en': 'Medium'},
      ),
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
      key: Ts746ReorderedIssueSyncRepository.issueAKey,
      summary: Ts746ReorderedIssueSyncRepository.issueASummary,
      storagePath: Ts746ReorderedIssueSyncRepository.issueAPath,
      priority: IssuePriority.high,
      priorityId: 'high',
      description:
          'Issue-A becomes the first visible row once Issue-B loses priority.',
    ),
    _issue(
      key: Ts746ReorderedIssueSyncRepository.issueBKey,
      summary: Ts746ReorderedIssueSyncRepository.issueBSummary,
      storagePath: Ts746ReorderedIssueSyncRepository.issueBPath,
      priority: IssuePriority.highest,
      priorityId: 'highest',
      description: Ts746ReorderedIssueSyncRepository.initialIssueBDescription,
    ),
    _issue(
      key: Ts746ReorderedIssueSyncRepository.issueCKey,
      summary: Ts746ReorderedIssueSyncRepository.issueCSummary,
      storagePath: Ts746ReorderedIssueSyncRepository.issueCPath,
      priority: IssuePriority.medium,
      priorityId: 'medium',
      description: 'Issue-C stays between the top and bottom rows.',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts746ReorderedIssueSyncRepository.issueAKey,
        path: Ts746ReorderedIssueSyncRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts746ReorderedIssueSyncRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts746ReorderedIssueSyncRepository.openStatusId,
        priorityId: 'high',
        assignee: 'qa-user',
        labels: const <String>['search'],
        updatedLabel: '1 minute ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts746ReorderedIssueSyncRepository.issueBKey,
        path: Ts746ReorderedIssueSyncRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts746ReorderedIssueSyncRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts746ReorderedIssueSyncRepository.openStatusId,
        priorityId: 'highest',
        assignee: 'qa-user',
        labels: const <String>['search'],
        updatedLabel: 'just now',
      ),
      RepositoryIssueIndexEntry(
        key: Ts746ReorderedIssueSyncRepository.issueCKey,
        path: Ts746ReorderedIssueSyncRepository.issueCPath,
        childKeys: <String>[],
        summary: Ts746ReorderedIssueSyncRepository.issueCSummary,
        issueTypeId: 'story',
        statusId: Ts746ReorderedIssueSyncRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: const <String>['search'],
        updatedLabel: '2 minutes ago',
      ),
    ],
  ),
);

TrackerSnapshot _snapshotWithReorderedSelectedIssue(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      for (final issue in snapshot.issues)
        if (issue.key == Ts746ReorderedIssueSyncRepository.issueBKey)
          TrackStateIssue(
            key: issue.key,
            project: issue.project,
            issueType: issue.issueType,
            issueTypeId: issue.issueTypeId,
            status: issue.status,
            statusId: issue.statusId,
            priority: IssuePriority.low,
            priorityId: 'low',
            summary: issue.summary,
            description:
                Ts746ReorderedIssueSyncRepository.updatedIssueBDescription,
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
            updatedLabel: 'moments ago',
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
          )
        else
          issue,
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        for (final entry in snapshot.repositoryIndex.entries)
          if (entry.key == Ts746ReorderedIssueSyncRepository.issueBKey)
            entry.copyWith(priorityId: 'low', updatedLabel: 'moments ago')
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
  required IssuePriority priority,
  required String priorityId,
  required String description,
}) {
  return TrackStateIssue(
    key: key,
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: IssueStatus.todo,
    statusId: Ts746ReorderedIssueSyncRepository.openStatusId,
    priority: priority,
    priorityId: priorityId,
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
    updatedLabel: 'just now',
    acceptanceCriteria: const <String>[
      'Keep the active query visible after refresh.',
      'Keep the selected issue highlighted even if sorting changes its index.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# $summary',
  );
}
