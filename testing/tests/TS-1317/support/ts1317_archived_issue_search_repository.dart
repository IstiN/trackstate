import 'dart:typed_data';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts1317ArchivedIssueSearchRepository extends DemoTrackStateRepository {
  Ts1317ArchivedIssueSearchRepository();

  static const JqlSearchService _searchService = JqlSearchService();

  static const ProjectConfig _project = ProjectConfig(
    key: 'TRACK',
    name: 'TrackState.AI',
    repository: 'IstiN/trackstate',
    branch: 'main',
    defaultLocale: 'en',
    supportedLocales: <String>['en'],
    issueTypeDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'story',
        name: 'Story',
        localizedLabels: <String, String>{'en': 'Story'},
      ),
    ],
    statusDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'todo',
        name: 'To Do',
        category: 'new',
        localizedLabels: <String, String>{'en': 'To Do'},
      ),
      TrackStateConfigEntry(
        id: 'done',
        name: 'Done',
        category: 'done',
        localizedLabels: <String, String>{'en': 'Done'},
      ),
    ],
    fieldDefinitions: <TrackStateFieldDefinition>[
      TrackStateFieldDefinition(
        id: 'summary',
        name: 'Summary',
        type: 'string',
        required: true,
        reserved: true,
        localizedLabels: <String, String>{'en': 'Summary'},
      ),
      TrackStateFieldDefinition(
        id: 'description',
        name: 'Description',
        type: 'markdown',
        required: false,
        reserved: true,
        localizedLabels: <String, String>{'en': 'Description'},
      ),
    ],
    workflowDefinitions: <TrackStateWorkflowDefinition>[
      TrackStateWorkflowDefinition(
        id: 'default',
        name: 'Default Workflow',
        statusIds: <String>['todo', 'done'],
        transitions: <TrackStateWorkflowTransition>[
          TrackStateWorkflowTransition(
            id: 'finish',
            name: 'Finish',
            fromStatusId: 'todo',
            toStatusId: 'done',
          ),
        ],
      ),
    ],
    priorityDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'high',
        name: 'High',
        localizedLabels: <String, String>{'en': 'High'},
      ),
    ],
  );

  static const RepositoryIndex _repositoryIndex = RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: 'TRACK-1317-1',
        path: 'TRACK/TRACK-1317-1/main.md',
        childKeys: <String>[],
        isArchived: false,
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-1317-2',
        path: 'TRACK/TRACK-1317-2/main.md',
        childKeys: <String>[],
        isArchived: true,
      ),
    ],
  );

  static const TrackerSnapshot _snapshot = TrackerSnapshot(
    project: _project,
    issues: <TrackStateIssue>[
      _activeIssue,
      _archivedIssue,
    ],
    repositoryIndex: _repositoryIndex,
    readiness: TrackerBootstrapReadiness(
      sectionStates: <TrackerSectionKey, TrackerLoadState>{
        TrackerSectionKey.dashboard: TrackerLoadState.ready,
        TrackerSectionKey.board: TrackerLoadState.ready,
        TrackerSectionKey.search: TrackerLoadState.ready,
        TrackerSectionKey.hierarchy: TrackerLoadState.ready,
        TrackerSectionKey.settings: TrackerLoadState.ready,
      },
      domainStates: <TrackerDataDomain, TrackerLoadState>{
        TrackerDataDomain.projectMeta: TrackerLoadState.ready,
        TrackerDataDomain.issueSummaries: TrackerLoadState.ready,
        TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
        TrackerDataDomain.issueDetails: TrackerLoadState.ready,
      },
    ),
  );

  static const TrackStateIssue _activeIssue = TrackStateIssue(
    key: 'TRACK-1317-1',
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: IssueStatus.todo,
    statusId: 'todo',
    priority: IssuePriority.high,
    priorityId: 'high',
    summary: 'Active search issue',
    description: 'Visible issue that should survive the active-search filter.',
    assignee: 'QA User',
    reporter: 'QA User',
    labels: <String>['search', 'active'],
    components: <String>[],
    fixVersionIds: <String>[],
    watchers: <String>[],
    customFields: <String, Object?>{},
    parentKey: null,
    epicKey: null,
    parentPath: null,
    epicPath: null,
    progress: 0,
    updatedLabel: 'just now',
    acceptanceCriteria: <String>[],
    comments: <IssueComment>[],
    links: <IssueLink>[],
    attachments: <IssueAttachment>[],
    isArchived: false,
    storagePath: 'TRACK/TRACK-1317-1/main.md',
  );

  static const TrackStateIssue _archivedIssue = TrackStateIssue(
    key: 'TRACK-1317-2',
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: IssueStatus.todo,
    statusId: 'todo',
    priority: IssuePriority.high,
    priorityId: 'high',
    summary: 'Archived search issue',
    description: 'Archived issue that must never surface in active search.',
    assignee: 'QA User',
    reporter: 'QA User',
    labels: <String>['search', 'archived'],
    components: <String>[],
    fixVersionIds: <String>[],
    watchers: <String>[],
    customFields: <String, Object?>{},
    parentKey: null,
    epicKey: null,
    parentPath: null,
    epicPath: null,
    progress: 0,
    updatedLabel: 'just now',
    acceptanceCriteria: <String>[],
    comments: <IssueComment>[],
    links: <IssueLink>[],
    attachments: <IssueAttachment>[],
    isArchived: true,
    storagePath: 'TRACK/TRACK-1317-2/main.md',
  );

  final List<String> searchQueries = <String>[];
  int loadSnapshotCalls = 0;
  int connectCalls = 0;

  @override
  bool get usesLocalPersistence => true;

  @override
  bool get supportsGitHubAuth => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    connectCalls += 1;
    return const RepositoryUser(login: 'qa-user', displayName: 'QA User');
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    loadSnapshotCalls += 1;
    return _snapshot;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    searchQueries.add(jql);
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
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException('TS-1317 fixture is read-only.');

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException('TS-1317 fixture is read-only.');

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw const TrackStateRepositoryException('TS-1317 fixture is read-only.');
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      throw const TrackStateRepositoryException('TS-1317 fixture is read-only.');

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async =>
      throw const TrackStateRepositoryException('TS-1317 fixture is read-only.');

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) async =>
      throw const TrackStateRepositoryException('TS-1317 fixture is read-only.');

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
    String? sourceName,
  }) async =>
      throw const TrackStateRepositoryException('TS-1317 fixture is read-only.');

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) async =>
      const <IssueHistoryEntry>[];
}
