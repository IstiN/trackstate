import 'dart:typed_data';

import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts447PostAuthResumeFixture {
  Ts447PostAuthResumeFixture() : repository = Ts447PostAuthResumeRepository();

  static const String issueKey = 'TRACK-447';
  static const String issueSummary =
      'Authenticated startup recovery resumes exactly once';
  static const String startupRecoveryTitle = 'GitHub startup limit reached';
  static const String startupRecoveryMessage =
      'Hosted startup loaded the minimum app-shell data, but GitHub rate-limited a deferred repository read. Retry later or connect GitHub for a higher limit to resume full hosted reads.';
  static const String connectedBanner =
      'Connected as ts-447-user to IstiN/trackstate. Drag cards to commit status changes.';

  final Ts447PostAuthResumeRepository repository;
}

class Ts447PostAuthResumeRepository implements TrackStateRepository {
  static const String _requestPath = 'repos/IstiN/trackstate/contents/TRACK';
  static const RepositoryUser _user = RepositoryUser(
    login: 'ts-447-user',
    displayName: 'TS-447 Tester',
  );
  static const JqlSearchService _searchService = JqlSearchService();
  static final DateTime _retryAfter = DateTime.utc(2026, 5, 12, 7, 30);

  static const ProjectConfig _project = ProjectConfig(
    key: 'TRACK',
    name: 'TrackState.AI',
    repository: 'IstiN/trackstate',
    branch: 'main',
    defaultLocale: 'en',
    issueTypeDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'story',
        name: 'Story',
        localizedLabels: {'en': 'Story'},
        workflowId: 'default',
      ),
    ],
    statusDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'todo',
        name: 'To Do',
        category: 'new',
        localizedLabels: {'en': 'To Do'},
      ),
      TrackStateConfigEntry(
        id: 'in-progress',
        name: 'In Progress',
        category: 'indeterminate',
        localizedLabels: {'en': 'In Progress'},
      ),
      TrackStateConfigEntry(
        id: 'done',
        name: 'Done',
        category: 'done',
        localizedLabels: {'en': 'Done'},
      ),
    ],
    fieldDefinitions: <TrackStateFieldDefinition>[
      TrackStateFieldDefinition(
        id: 'summary',
        name: 'Summary',
        type: 'string',
        required: true,
        reserved: true,
        localizedLabels: {'en': 'Summary'},
      ),
      TrackStateFieldDefinition(
        id: 'description',
        name: 'Description',
        type: 'markdown',
        required: false,
        reserved: true,
        localizedLabels: {'en': 'Description'},
      ),
    ],
    workflowDefinitions: <TrackStateWorkflowDefinition>[
      TrackStateWorkflowDefinition(
        id: 'default',
        name: 'Default Workflow',
        statusIds: <String>['todo', 'in-progress', 'done'],
        transitions: <TrackStateWorkflowTransition>[
          TrackStateWorkflowTransition(
            id: 'start',
            name: 'Start progress',
            fromStatusId: 'todo',
            toStatusId: 'in-progress',
          ),
          TrackStateWorkflowTransition(
            id: 'complete',
            name: 'Complete',
            fromStatusId: 'in-progress',
            toStatusId: 'done',
          ),
        ],
      ),
    ],
    priorityDefinitions: <TrackStateConfigEntry>[
      TrackStateConfigEntry(
        id: 'high',
        name: 'High',
        localizedLabels: {'en': 'High'},
      ),
    ],
  );

  static const TrackStateIssue _issue = TrackStateIssue(
    key: Ts447PostAuthResumeFixture.issueKey,
    project: 'TRACK',
    issueType: IssueType.story,
    issueTypeId: 'story',
    status: IssueStatus.inProgress,
    statusId: 'in-progress',
    priority: IssuePriority.high,
    priorityId: 'high',
    summary: Ts447PostAuthResumeFixture.issueSummary,
    description:
        'Validate that GitHub authentication resumes hosted startup once and requires explicit retry after a second rate-limit failure.',
    assignee: 'ts-447-user',
    reporter: 'ts-447-user',
    labels: <String>['auth', 'startup-recovery'],
    components: <String>[],
    fixVersionIds: <String>[],
    watchers: <String>['ts-447-user'],
    customFields: <String, Object?>{},
    parentKey: null,
    epicKey: null,
    parentPath: null,
    epicPath: null,
    progress: 0.4,
    updatedLabel: 'just now',
    acceptanceCriteria: <String>[
      'Authentication triggers one automatic startup resume.',
      'A failed resumed load does not auto-retry again.',
      'Further resume attempts require explicit Retry.',
    ],
    comments: <IssueComment>[],
    links: <IssueLink>[],
    attachments: <IssueAttachment>[],
    isArchived: false,
    storagePath: 'TRACK/TRACK-447/main.md',
  );

  static const RepositoryIndex _repositoryIndex = RepositoryIndex(
    entries: <RepositoryIssueIndexEntry>[
      RepositoryIssueIndexEntry(
        key: Ts447PostAuthResumeFixture.issueKey,
        path: 'TRACK/TRACK-447/main.md',
        childKeys: <String>[],
      ),
    ],
  );

  static final TrackerSnapshot _startupRecoverySnapshot = TrackerSnapshot(
    project: _project,
    issues: const <TrackStateIssue>[_issue],
    repositoryIndex: _repositoryIndex,
    readiness: const TrackerBootstrapReadiness(
      sectionStates: <TrackerSectionKey, TrackerLoadState>{
        TrackerSectionKey.dashboard: TrackerLoadState.partial,
        TrackerSectionKey.board: TrackerLoadState.partial,
        TrackerSectionKey.search: TrackerLoadState.partial,
        TrackerSectionKey.hierarchy: TrackerLoadState.partial,
        TrackerSectionKey.settings: TrackerLoadState.ready,
      },
      domainStates: <TrackerDataDomain, TrackerLoadState>{
        TrackerDataDomain.projectMeta: TrackerLoadState.ready,
        TrackerDataDomain.issueSummaries: TrackerLoadState.partial,
        TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
        TrackerDataDomain.issueDetails: TrackerLoadState.loading,
      },
    ),
    startupRecovery: TrackerStartupRecovery(
      kind: TrackerStartupRecoveryKind.githubRateLimit,
      failedPath: _requestPath,
      retryAfter: _retryAfter,
    ),
  );

  static const TrackerSnapshot _healthySnapshot = TrackerSnapshot(
    project: _project,
    issues: <TrackStateIssue>[_issue],
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

  bool _authenticated = false;
  int _resumeFailuresRemaining = 1;

  int loadSnapshotCalls = 0;
  int searchIssuePageCalls = 0;
  int connectCalls = 0;

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  TrackerSnapshot get _searchSnapshot =>
      _authenticated && _resumeFailuresRemaining == 0
      ? _healthySnapshot
      : _startupRecoverySnapshot;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async {
    connectCalls += 1;
    _authenticated = true;
    return _user;
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    loadSnapshotCalls += 1;
    if (_authenticated && _resumeFailuresRemaining > 0) {
      _resumeFailuresRemaining -= 1;
      throw GitHubRateLimitException(
        message:
            'GitHub rate limit prevented TrackState from resuming hosted startup after authentication.',
        requestPath: _requestPath,
        statusCode: 403,
        retryAfter: _retryAfter,
      );
    }
    return _authenticated ? _healthySnapshot : _startupRecoverySnapshot;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    searchIssuePageCalls += 1;
    final snapshot = _searchSnapshot;
    return _searchService.search(
      issues: snapshot.issues,
      project: snapshot.project,
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
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) => throw const TrackStateRepositoryException(
    'TS-447 fixture does not support creating issues.',
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => throw const TrackStateRepositoryException(
    'TS-447 fixture does not support editing issue descriptions.',
  );

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) => throw const TrackStateRepositoryException(
    'TS-447 fixture does not support editing issue status.',
  );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      throw const TrackStateRepositoryException(
        'TS-447 fixture does not support deleting issues.',
      );

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      throw const TrackStateRepositoryException(
        'TS-447 fixture does not support archiving issues.',
      );

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) =>
      throw const TrackStateRepositoryException(
        'TS-447 fixture does not support issue comments.',
      );

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) => throw const TrackStateRepositoryException(
    'TS-447 fixture does not support attachment uploads.',
  );

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      throw const TrackStateRepositoryException(
        'TS-447 fixture does not support attachment downloads.',
      );

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      throw const TrackStateRepositoryException(
        'TS-447 fixture does not support loading issue history.',
      );
}
