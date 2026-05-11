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
    'TS-314 JQL Search supports IS EMPTY and IS NOT EMPTY for nullable fields',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const emptyAssigneeQuery = 'assignee IS EMPTY AND project = TRACK';
      const parentNotEmptyQuery =
          'parent IS NOT EMPTY AND issueType = "Sub-task"';
      const emptyEpicQuery = 'epic IS EMPTY AND issueType = Story';
      const unsupportedFieldQuery = 'status IS EMPTY';
      const unsupportedFieldError =
          'Search failed: JqlSearchException: Field "status" does not support IS EMPTY.';

      const unassignedStoryLabel =
          'Open TRACK-201 Unassigned story without epic';
      const linkedStoryLabel = 'Open TRACK-203 Story linked to the parser epic';
      const childSubtaskLabel = 'Open TRACK-204 Sub-task with parent reference';
      const orphanSubtaskLabel = 'Open TRACK-205 Sub-task without parent link';
      const assignedStoryLabel = 'Open TRACK-202 Assigned story without epic';

      try {
        await screen.pump(const _Ts314NullableFieldSearchRepository());
        screen.expectLocalRuntimeChrome();
        await screen.openSection('JQL Search');

        await _expectSearchMatches(
          screen,
          query: emptyAssigneeQuery,
          expectedVisibleLabels: const {unassignedStoryLabel},
          expectedSummaryText: '1 issue',
          failingStep: 1,
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-202',
          'Assigned story without epic',
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-203',
          'Story linked to the parser epic',
        );

        await _expectSearchMatches(
          screen,
          query: parentNotEmptyQuery,
          expectedVisibleLabels: const {childSubtaskLabel},
          expectedSummaryText: '1 issue',
          failingStep: 2,
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-205',
          'Sub-task without parent link',
        );

        await _expectSearchMatches(
          screen,
          query: emptyEpicQuery,
          expectedVisibleLabels: const {
            unassignedStoryLabel,
            assignedStoryLabel,
          },
          expectedSummaryText: '2 issues',
          failingStep: 3,
        );
        screen.expectIssueSearchResultAbsent(
          'TRACK-203',
          'Story linked to the parser epic',
        );

        await screen.searchIssues(unsupportedFieldQuery);

        expect(
          await screen.isMessageBannerVisibleContaining(unsupportedFieldError),
          isTrue,
          reason:
              'Step 4 failed: running "$unsupportedFieldQuery" did not show the '
              'expected explicit parsing error. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot().toSet(),
          equals(const {unassignedStoryLabel, assignedStoryLabel}),
          reason:
              'Step 4 failed: the unsupported empty-check query changed the '
              'visible results instead of preserving the last valid search '
              'state. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible('2 issues'),
          isTrue,
          reason:
              'Step 4 failed: after the unsupported empty-check query, the '
              'JQL Search panel no longer showed the previous visible summary. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
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

class _Ts314NullableFieldSearchRepository implements TrackStateRepository {
  const _Ts314NullableFieldSearchRepository();

  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const JqlSearchService _searchService = JqlSearchService();

  static final List<TrackStateIssue> _issues = <TrackStateIssue>[
    _Ts314IssueFactory.story(
      key: 'TRACK-201',
      summary: 'Unassigned story without epic',
      assignee: ' ',
    ),
    _Ts314IssueFactory.story(
      key: 'TRACK-202',
      summary: 'Assigned story without epic',
      assignee: 'Dana Developer',
    ),
    _Ts314IssueFactory.story(
      key: 'TRACK-203',
      summary: 'Story linked to the parser epic',
      assignee: 'Parker Product',
      epicKey: 'TRACK-900',
    ),
    _Ts314IssueFactory.subtask(
      key: 'TRACK-204',
      summary: 'Sub-task with parent reference',
      assignee: 'Chris QA',
      parentKey: 'TRACK-201',
      epicKey: 'TRACK-900',
    ),
    _Ts314IssueFactory.subtask(
      key: 'TRACK-205',
      summary: 'Sub-task without parent link',
      assignee: 'Chris QA',
      parentKey: null,
      epicKey: 'TRACK-900',
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
    return TrackerSnapshot(project: snapshot.project, issues: _issues);
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
        'TS-314 nullable-field fixture is read-only.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'TS-314 nullable-field fixture is read-only.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw const TrackStateRepositoryException(
      'TS-314 nullable-field fixture does not create issues.',
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

abstract final class _Ts314IssueFactory {
  static const String _projectKey = 'TRACK';
  static const String _storyTypeId = 'story';
  static const String _subtaskTypeId = 'subtask';
  static const String _statusId = 'todo';

  static TrackStateIssue story({
    required String key,
    required String summary,
    required String assignee,
    String? epicKey,
  }) {
    return _issue(
      key: key,
      summary: summary,
      assignee: assignee,
      issueType: IssueType.story,
      issueTypeId: _storyTypeId,
      epicKey: epicKey,
    );
  }

  static TrackStateIssue subtask({
    required String key,
    required String summary,
    required String assignee,
    String? parentKey,
    String? epicKey,
  }) {
    return _issue(
      key: key,
      summary: summary,
      assignee: assignee,
      issueType: IssueType.subtask,
      issueTypeId: _subtaskTypeId,
      parentKey: parentKey,
      epicKey: epicKey,
    );
  }

  static TrackStateIssue _issue({
    required String key,
    required String summary,
    required String assignee,
    required IssueType issueType,
    required String issueTypeId,
    String? parentKey,
    String? epicKey,
  }) {
    return TrackStateIssue(
      key: key,
      project: _projectKey,
      issueType: issueType,
      issueTypeId: issueTypeId,
      status: IssueStatus.todo,
      statusId: _statusId,
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: summary,
      description: '$summary description.',
      assignee: assignee,
      reporter: 'Taylor QA',
      labels: const <String>['jql-nullability'],
      components: const <String>[],
      fixVersionIds: const <String>[],
      watchers: const <String>[],
      customFields: const <String, Object?>{},
      parentKey: parentKey,
      epicKey: epicKey,
      parentPath: null,
      epicPath: null,
      progress: 0,
      updatedLabel: 'today',
      acceptanceCriteria: const <String>[],
      comments: const <IssueComment>[],
      links: const <IssueLink>[],
      attachments: const <IssueAttachment>[],
      isArchived: false,
    );
  }
}
