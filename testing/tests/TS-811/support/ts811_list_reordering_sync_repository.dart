import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts811ListReorderingSyncRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts811ListReorderingSyncRepository() : super(snapshot: _initialSnapshot);

  static const String issueAKey = 'TRACK-811-A';
  static const String issueBKey = 'TRACK-811-B';
  static const String issueCKey = 'TRACK-811-C';

  static const String issueASummary =
      'Selected issue must remain selected after reordering';
  static const String issueBSummary =
      'Priority promotion moves this issue above the selected row';
  static const String issueCSummary =
      'Lower-priority issue stays below the reordered pair';

  static const String issueAPath = '$issueAKey/main.md';
  static const String issueBPath = '$issueBKey/main.md';
  static const String issueCPath = '$issueCKey/main.md';

  static const String todoStatusId = 'todo';
  static const String inProgressStatusId = 'in-progress';
  static const String doneStatusId = 'done';
  static const String query =
      'project = TRACK AND status != Done ORDER BY priority DESC';

  static const String issueADescription =
      'Issue-A detail should stay open while Issue-B moves above it after sync refresh.';
  static const String issueBDescription =
      'Issue-B starts below the selected issue and becomes the new top row after its priority increases.';

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts811-user',
    displayName: 'TS-811 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingPromotionRefresh = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts811-revision-$_revisionSerial';

  void scheduleIssueBPromotionRefresh() {
    _currentSnapshot = _snapshotWithIssueBPromoted(_currentSnapshot);
    _pendingPromotionRefresh = true;
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
    if (_pendingPromotionRefresh) {
      _pendingPromotionRefresh = false;
      _revisionSerial += 1;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts811-session',
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
        sessionRevision: 'ts811-session',
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
        id: Ts811ListReorderingSyncRepository.todoStatusId,
        name: 'To Do',
        localizedLabels: <String, String>{'en': 'To Do'},
        category: 'new',
      ),
      TrackStateConfigEntry(
        id: Ts811ListReorderingSyncRepository.inProgressStatusId,
        name: 'In Progress',
        localizedLabels: <String, String>{'en': 'In Progress'},
        category: 'indeterminate',
      ),
      TrackStateConfigEntry(
        id: Ts811ListReorderingSyncRepository.doneStatusId,
        name: 'Done',
        localizedLabels: <String, String>{'en': 'Done'},
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
      key: Ts811ListReorderingSyncRepository.issueAKey,
      summary: Ts811ListReorderingSyncRepository.issueASummary,
      storagePath: Ts811ListReorderingSyncRepository.issueAPath,
      status: IssueStatus.inProgress,
      statusId: Ts811ListReorderingSyncRepository.inProgressStatusId,
      priority: IssuePriority.high,
      priorityId: 'high',
      description: Ts811ListReorderingSyncRepository.issueADescription,
    ),
    _issue(
      key: Ts811ListReorderingSyncRepository.issueBKey,
      summary: Ts811ListReorderingSyncRepository.issueBSummary,
      storagePath: Ts811ListReorderingSyncRepository.issueBPath,
      status: IssueStatus.todo,
      statusId: Ts811ListReorderingSyncRepository.todoStatusId,
      priority: IssuePriority.medium,
      priorityId: 'medium',
      description: Ts811ListReorderingSyncRepository.issueBDescription,
    ),
    _issue(
      key: Ts811ListReorderingSyncRepository.issueCKey,
      summary: Ts811ListReorderingSyncRepository.issueCSummary,
      storagePath: Ts811ListReorderingSyncRepository.issueCPath,
      status: IssueStatus.todo,
      statusId: Ts811ListReorderingSyncRepository.todoStatusId,
      priority: IssuePriority.low,
      priorityId: 'low',
      description:
          'Issue-C should remain below the selected issue after the refresh.',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts811ListReorderingSyncRepository.issueAKey,
        path: Ts811ListReorderingSyncRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts811ListReorderingSyncRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts811ListReorderingSyncRepository.inProgressStatusId,
        priorityId: 'high',
        assignee: 'qa-user',
        labels: const <String>['search'],
        updatedLabel: '1 minute ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts811ListReorderingSyncRepository.issueBKey,
        path: Ts811ListReorderingSyncRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts811ListReorderingSyncRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts811ListReorderingSyncRepository.todoStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: const <String>['search'],
        updatedLabel: '2 minutes ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts811ListReorderingSyncRepository.issueCKey,
        path: Ts811ListReorderingSyncRepository.issueCPath,
        childKeys: <String>[],
        summary: Ts811ListReorderingSyncRepository.issueCSummary,
        issueTypeId: 'story',
        statusId: Ts811ListReorderingSyncRepository.todoStatusId,
        priorityId: 'low',
        assignee: 'qa-user',
        labels: const <String>['search'],
        updatedLabel: '3 minutes ago',
      ),
    ],
  ),
);

TrackerSnapshot _snapshotWithIssueBPromoted(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      for (final issue in snapshot.issues)
        if (issue.key == Ts811ListReorderingSyncRepository.issueBKey)
          TrackStateIssue(
            key: issue.key,
            project: issue.project,
            issueType: issue.issueType,
            issueTypeId: issue.issueTypeId,
            status: issue.status,
            statusId: issue.statusId,
            priority: IssuePriority.highest,
            priorityId: 'highest',
            summary: issue.summary,
            description: issue.description,
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
          if (entry.key == Ts811ListReorderingSyncRepository.issueBKey)
            entry.copyWith(priorityId: 'highest', updatedLabel: 'moments ago')
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
  required IssueStatus status,
  required String statusId,
  required IssuePriority priority,
  required String priorityId,
  required String description,
}) {
  return TrackStateIssue(
    key: key,
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: status,
    statusId: statusId,
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
      'Keep the selected issue bound to its stable ID when the list order changes.',
      'Move the selected row to its new position without transferring the highlight to another issue.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# $summary',
  );
}
