import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-313 JQL Search evaluates canonical fields and quoted multi-word values',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const firstQuery = 'status = "In Progress" AND issueType = "Sub-task"';
      const secondQuery = 'status != Done AND project = TRACK';

      const inProgressSubtaskLabel =
          'Open TRACK-301 Release checklist sub-task';
      const doneSubtaskLabel = 'Open TRACK-302 Completed release sub-task';
      const inProgressStoryLabel = 'Open TRACK-303 Story still moving';
      const todoStoryLabel = 'Open TRACK-304 Story waiting for development';
      const doneBugLabel = 'Open TRACK-305 Done regression fix';
      const statusDecoyLabel =
          'Open TRACK-306 Status decoy looks in progress sub-task';
      const externalProjectLabel = 'Open OTHER-401 External project work item';
      const issueTypeDecoyLabel =
          'Open OTHER-402 Issue-type decoy looks in progress sub-task';

      try {
        await screen.pump(const _Ts313CanonicalFieldRepository());
        screen.expectLocalRuntimeChrome();
        await screen.openSection('JQL Search');

        await _expectSearchMatches(
          screen,
          query: firstQuery,
          expectedVisibleLabels: const {inProgressSubtaskLabel},
          expectedSummaryText: '1 issue',
          failingStep: 1,
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-302',
          'Completed release sub-task',
        );
        screen.expectIssueSearchResultAbsent('TRACK-303', 'Story still moving');
        screen.expectIssueSearchResultAbsent(
          'TRACK-304',
          'Story waiting for development',
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-305',
          'Done regression fix',
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-306',
          'Status decoy looks in progress sub-task',
        );
        screen.expectIssueSearchResultAbsent(
          'OTHER-401',
          'External project work item',
        );
        screen.expectIssueSearchResultAbsent(
          'OTHER-402',
          'Issue-type decoy looks in progress sub-task',
        );

        await _expectSearchMatches(
          screen,
          query: secondQuery,
          expectedVisibleLabels: const {
            inProgressSubtaskLabel,
            inProgressStoryLabel,
            todoStoryLabel,
          },
          expectedSummaryText: '3 issues',
          failingStep: 2,
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-302',
          'Completed release sub-task',
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-305',
          'Done regression fix',
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-306',
          'Status decoy looks in progress sub-task',
        );
        screen.expectIssueSearchResultAbsent(
          'OTHER-401',
          'External project work item',
        );
        screen.expectIssueSearchResultAbsent(
          'OTHER-402',
          'Issue-type decoy looks in progress sub-task',
        );

        expect(
          screen.visibleIssueSearchResultLabelsSnapshot().toSet(),
          equals(const {
            inProgressSubtaskLabel,
            inProgressStoryLabel,
            todoStoryLabel,
          }),
          reason:
              'Human-style verification failed: the visible JQL Search issue '
              'rows after "$secondQuery" were not the expected stable keys. '
              'Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}. '
              'Hidden rows should still exclude $doneSubtaskLabel, '
              '$statusDecoyLabel, '
              '$doneBugLabel, $externalProjectLabel, and '
              '$issueTypeDecoyLabel.',
        );
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<void> _expectSearchMatches(
  TrackStateAppComponent screen, {
  required String query,
  required Set<String> expectedVisibleLabels,
  required String expectedSummaryText,
  required int failingStep,
}) async {
  await screen.searchIssues(query);

  expect(
    await screen.readJqlSearchFieldValue(),
    query,
    reason:
        'Step $failingStep failed: the JQL Search field did not keep the exact '
        'query "$query" after submission.',
  );
  expect(
    await screen.isMessageBannerVisibleContaining('Search failed:'),
    isFalse,
    reason:
        'Step $failingStep failed: a visible search failure banner appeared '
        'while running the supported query "$query". Visible texts: '
        '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible semantics: '
        '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
  expect(
    screen.visibleIssueSearchResultLabelsSnapshot().toSet(),
    equals(expectedVisibleLabels),
    reason:
        'Step $failingStep failed: the visible JQL Search results for "$query" '
        'were ${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())} '
        'instead of ${_formatSnapshot(expectedVisibleLabels.toList())}.',
  );
  expect(
    await screen.isTextVisible(expectedSummaryText),
    isTrue,
    reason:
        'Step $failingStep failed: the JQL Search panel did not show the '
        'visible "$expectedSummaryText" summary for "$query". Visible texts: '
        '${_formatSnapshot(screen.visibleTextsSnapshot())}.',
  );
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}

class _Ts313CanonicalFieldRepository implements TrackStateRepository {
  const _Ts313CanonicalFieldRepository();

  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const JqlSearchService _searchService = JqlSearchService();

  static const String _trackProjectKey = 'TRACK';
  static const String _trackProjectName = 'Track Project';
  static const String _storyTypeId = 'story-type-id';
  static const String _subtaskTypeId = 'subtask-type-id';
  static const String _bugTypeId = 'bug-type-id';
  static const String _todoStatusId = 'todo-status-id';
  static const String _inProgressStatusId = 'in-progress-status-id';
  static const String _doneStatusId = 'done-status-id';

  static const List<TrackStateConfigEntry> _issueTypeDefinitions =
      <TrackStateConfigEntry>[
        TrackStateConfigEntry(id: _storyTypeId, name: 'Story'),
        TrackStateConfigEntry(id: _subtaskTypeId, name: 'Sub-task'),
        TrackStateConfigEntry(id: _bugTypeId, name: 'Bug'),
      ];

  static const List<TrackStateConfigEntry> _statusDefinitions =
      <TrackStateConfigEntry>[
        TrackStateConfigEntry(id: _todoStatusId, name: 'To Do'),
        TrackStateConfigEntry(id: _inProgressStatusId, name: 'In Progress'),
        TrackStateConfigEntry(id: _doneStatusId, name: 'Done'),
      ];

  static final List<TrackStateIssue> _issues = <TrackStateIssue>[
    _Ts313IssueFactory.subtask(
      key: 'TRACK-301',
      summary: 'Release checklist sub-task',
      project: _trackProjectKey,
      status: IssueStatus.inProgress,
      statusId: _inProgressStatusId,
    ),
    _Ts313IssueFactory.subtask(
      key: 'TRACK-302',
      summary: 'Completed release sub-task',
      project: _trackProjectKey,
      status: IssueStatus.done,
      statusId: _doneStatusId,
    ),
    _Ts313IssueFactory.story(
      key: 'TRACK-303',
      summary: 'Story still moving',
      project: _trackProjectKey,
      status: IssueStatus.inProgress,
      statusId: _inProgressStatusId,
    ),
    _Ts313IssueFactory.story(
      key: 'TRACK-304',
      summary: 'Story waiting for development',
      project: _trackProjectKey,
      status: IssueStatus.todo,
      statusId: _todoStatusId,
    ),
    _Ts313IssueFactory.bug(
      key: 'TRACK-305',
      summary: 'Done regression fix',
      project: _trackProjectKey,
      status: IssueStatus.done,
      statusId: _doneStatusId,
    ),
    _Ts313IssueFactory.issue(
      key: 'TRACK-306',
      summary: 'Status decoy looks in progress sub-task',
      project: _trackProjectKey,
      issueType: IssueType.subtask,
      issueTypeId: _subtaskTypeId,
      status: IssueStatus.inProgress,
      statusId: _doneStatusId,
    ),
    _Ts313IssueFactory.story(
      key: 'OTHER-401',
      summary: 'External project work item',
      project: 'OTHER',
      status: IssueStatus.inProgress,
      statusId: _inProgressStatusId,
    ),
    _Ts313IssueFactory.issue(
      key: 'OTHER-402',
      summary: 'Issue-type decoy looks in progress sub-task',
      project: 'OTHER',
      issueType: IssueType.subtask,
      issueTypeId: _storyTypeId,
      status: IssueStatus.inProgress,
      statusId: _inProgressStatusId,
    ),
  ];

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await _delegate.loadSnapshot();
    return TrackerSnapshot(
      project: ProjectConfig(
        key: _trackProjectKey,
        name: _trackProjectName,
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        defaultLocale: snapshot.project.defaultLocale,
        issueTypeDefinitions: _issueTypeDefinitions,
        statusDefinitions: _statusDefinitions,
        fieldDefinitions: snapshot.project.fieldDefinitions,
        priorityDefinitions: snapshot.project.priorityDefinitions,
        versionDefinitions: snapshot.project.versionDefinitions,
        componentDefinitions: snapshot.project.componentDefinitions,
        resolutionDefinitions: snapshot.project.resolutionDefinitions,
      ),
      issues: _issues,
    );
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final snapshot = await loadSnapshot();
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
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'TS-313 canonical field fixture is read-only.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'TS-313 canonical field fixture is read-only.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw const TrackStateRepositoryException(
      'TS-313 canonical field fixture does not create issues.',
    );
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'now');

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'now');

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue;

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];
}

abstract final class _Ts313IssueFactory {
  static const String _priorityId = 'medium';

  static TrackStateIssue issue({
    required String key,
    required String summary,
    required String project,
    required IssueType issueType,
    required String issueTypeId,
    required IssueStatus status,
    required String statusId,
  }) {
    return _issue(
      key: key,
      project: project,
      summary: summary,
      issueType: issueType,
      issueTypeId: issueTypeId,
      status: status,
      statusId: statusId,
    );
  }

  static TrackStateIssue story({
    required String key,
    required String summary,
    required String project,
    required IssueStatus status,
    required String statusId,
  }) {
    return _issue(
      key: key,
      project: project,
      summary: summary,
      issueType: IssueType.story,
      issueTypeId: _Ts313CanonicalFieldRepository._storyTypeId,
      status: status,
      statusId: statusId,
    );
  }

  static TrackStateIssue subtask({
    required String key,
    required String summary,
    required String project,
    required IssueStatus status,
    required String statusId,
  }) {
    return _issue(
      key: key,
      project: project,
      summary: summary,
      issueType: IssueType.subtask,
      issueTypeId: _Ts313CanonicalFieldRepository._subtaskTypeId,
      status: status,
      statusId: statusId,
    );
  }

  static TrackStateIssue bug({
    required String key,
    required String summary,
    required String project,
    required IssueStatus status,
    required String statusId,
  }) {
    return _issue(
      key: key,
      project: project,
      summary: summary,
      issueType: IssueType.bug,
      issueTypeId: _Ts313CanonicalFieldRepository._bugTypeId,
      status: status,
      statusId: statusId,
    );
  }

  static TrackStateIssue _issue({
    required String key,
    required String project,
    required String summary,
    required IssueType issueType,
    required String issueTypeId,
    required IssueStatus status,
    required String statusId,
  }) {
    return TrackStateIssue(
      key: key,
      project: project,
      issueType: issueType,
      issueTypeId: issueTypeId,
      status: status,
      statusId: statusId,
      priority: IssuePriority.medium,
      priorityId: _priorityId,
      summary: summary,
      description: '$summary description.',
      assignee: 'Taylor QA',
      reporter: 'Taylor QA',
      labels: const <String>['jql-canonical-fields'],
      components: const <String>[],
      fixVersionIds: const <String>[],
      watchers: const <String>[],
      customFields: const <String, Object?>{},
      parentKey: null,
      epicKey: null,
      parentPath: null,
      epicPath: null,
      progress: 0,
      updatedLabel: 'today',
      acceptanceCriteria: const <String>[
        'Canonical JQL fields should map names to stable IDs.',
      ],
      comments: const <IssueComment>[],
      links: const <IssueLink>[],
      attachments: const <IssueAttachment>[],
      isArchived: false,
    );
  }
}
