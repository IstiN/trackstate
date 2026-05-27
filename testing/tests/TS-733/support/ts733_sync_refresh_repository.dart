import 'dart:async';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts733SyncRefreshRepository extends DemoTrackStateRepository
    implements WorkspaceSyncRepository {
  Ts733SyncRefreshRepository() : super(snapshot: _initialSnapshot);

  static const String issueAKey = 'TRACK-733-A';
  static const String issueBKey = 'TRACK-733-B';
  static const String issueASummary = 'Issue-A remains open after the sync';
  static const String issueBSummary = 'Issue-B starts selected before the sync';
  static const String issueAPath = 'TRACK-733-A/main.md';
  static const String issueBPath = 'TRACK-733-B/main.md';
  static const String openStatusId = 'open';
  static const String closedStatusId = 'closed';
  static const String query = 'status = Open';
  static const Duration automaticSyncWait = Duration(seconds: 61);

  static const JqlSearchService _searchService = JqlSearchService();
  static const RepositoryUser _connectedUser = RepositoryUser(
    login: 'ts733-user',
    displayName: 'TS-733 User',
  );

  TrackerSnapshot _currentSnapshot = _initialSnapshot;
  bool _pendingStatusRefresh = false;
  int _revisionSerial = 1;
  int _syncCheckCount = 0;

  int get syncCheckCount => _syncCheckCount;

  String get repositoryRevision => 'ts733-revision-$_revisionSerial';

  void scheduleIssueBClosure() {
    _currentSnapshot = _snapshotWithClosedIssueB(_currentSnapshot);
    _pendingStatusRefresh = true;
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
    if (_pendingStatusRefresh) {
      _pendingStatusRefresh = false;
      _revisionSerial += 1;
      return RepositorySyncCheck(
        state: RepositorySyncState(
          providerType: ProviderType.github,
          repositoryRevision: repositoryRevision,
          sessionRevision: 'ts733-session',
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
        sessionRevision: 'ts733-session',
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
        id: Ts733SyncRefreshRepository.openStatusId,
        name: 'Open',
        localizedLabels: <String, String>{'en': 'Open'},
        category: 'new',
      ),
      TrackStateConfigEntry(
        id: Ts733SyncRefreshRepository.closedStatusId,
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
      key: Ts733SyncRefreshRepository.issueAKey,
      summary: Ts733SyncRefreshRepository.issueASummary,
      storagePath: Ts733SyncRefreshRepository.issueAPath,
      status: IssueStatus.todo,
      statusId: Ts733SyncRefreshRepository.openStatusId,
      updatedLabel: '1 minute ago',
    ),
    _issue(
      key: Ts733SyncRefreshRepository.issueBKey,
      summary: Ts733SyncRefreshRepository.issueBSummary,
      storagePath: Ts733SyncRefreshRepository.issueBPath,
      status: IssueStatus.todo,
      statusId: Ts733SyncRefreshRepository.openStatusId,
      updatedLabel: 'just now',
    ),
  ],
  repositoryIndex: RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts733SyncRefreshRepository.issueAKey,
        path: Ts733SyncRefreshRepository.issueAPath,
        childKeys: <String>[],
        summary: Ts733SyncRefreshRepository.issueASummary,
        issueTypeId: 'story',
        statusId: Ts733SyncRefreshRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: '1 minute ago',
      ),
      RepositoryIssueIndexEntry(
        key: Ts733SyncRefreshRepository.issueBKey,
        path: Ts733SyncRefreshRepository.issueBPath,
        childKeys: <String>[],
        summary: Ts733SyncRefreshRepository.issueBSummary,
        issueTypeId: 'story',
        statusId: Ts733SyncRefreshRepository.openStatusId,
        priorityId: 'medium',
        assignee: 'qa-user',
        labels: <String>['search'],
        updatedLabel: 'just now',
      ),
    ],
  ),
);

TrackerSnapshot _snapshotWithClosedIssueB(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: <TrackStateIssue>[
      for (final issue in snapshot.issues)
        if (issue.key == Ts733SyncRefreshRepository.issueBKey)
          issue.copyWith(
            status: IssueStatus.done,
            statusId: Ts733SyncRefreshRepository.closedStatusId,
            updatedLabel: 'just now',
          )
        else
          issue,
    ],
    repositoryIndex: RepositoryIndex(
      entries: <RepositoryIssueIndexEntry>[
        for (final entry in snapshot.repositoryIndex.entries)
          if (entry.key == Ts733SyncRefreshRepository.issueBKey)
            entry.copyWith(
              statusId: Ts733SyncRefreshRepository.closedStatusId,
              updatedLabel: 'just now',
            )
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
  required String updatedLabel,
}) {
  return TrackStateIssue(
    key: key,
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: status,
    statusId: statusId,
    priority: IssuePriority.medium,
    priorityId: 'medium',
    summary: summary,
    description: '$summary description',
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
      'Keep the active query visible after background refresh.',
      'Clear the selected issue if it no longer matches the query.',
    ],
    comments: const <IssueComment>[],
    links: const <IssueLink>[],
    attachments: const <IssueAttachment>[],
    isArchived: false,
    storagePath: storagePath,
    rawMarkdown: '# $summary',
  );
}
