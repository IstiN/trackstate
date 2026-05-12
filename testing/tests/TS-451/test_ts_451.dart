import 'dart:typed_data';

import 'package:flutter/material.dart' show CircularProgressIndicator;
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
    'TS-451 keeps JQL Search visible with bootstrap-backed rows during initial hydration',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = _Ts451SearchHydrationRepository();

      const defaultQuery =
          'project = TRACK AND status != Done ORDER BY priority DESC';
      const firstPageSummary = 'Showing 6 of 8 issues';
      const bootstrapVisibleLabels = <String>[
        'Open TRACK-401 Highest priority bootstrap alpha',
        'Open TRACK-402 Highest priority bootstrap beta',
        'Open TRACK-403 High priority visible partial row',
        'Open TRACK-404 High priority non-blocking list shell',
        'Open TRACK-405 Medium priority hydration placeholder',
        'Open TRACK-406 Medium priority in-place completion',
      ];

      try {
        await screen.pump(repository);
        await screen.openSection('JQL Search');

        expect(
          repository.searchRequests,
          1,
          reason:
              'Precondition failed: opening the app should start exactly one initial JQL Search hydration request.',
        );
        expect(
          await screen.isTextVisible('JQL Search'),
          isTrue,
          reason:
              'Step 1 failed: the JQL Search heading was not visible while initial hydration was still pending.',
        );
        expect(
          await screen.isTextFieldVisible('Search issues'),
          isTrue,
          reason:
              'Step 2 failed: the Search issues field was replaced during hydration instead of staying visible.',
        );
        expect(
          await screen.readJqlSearchFieldValue(),
          defaultQuery,
          reason:
              'Step 2 failed: the visible search field did not keep the default query while initial hydration was pending.',
        );
        expect(
          await screen.isSemanticsLabelVisible('JQL Search Loading...'),
          isTrue,
          reason:
              'Step 2 failed: the search section did not expose its in-place loading banner during hydration.',
        );
        expect(
          find.byType(CircularProgressIndicator),
          findsNothing,
          reason:
              'Step 3 failed: a blocking CircularProgressIndicator replaced the visible search surface during hydration.',
        );
        expect(
          _baseSearchRowLabels(screen.visibleIssueSearchResultLabelsSnapshot()),
          equals(bootstrapVisibleLabels),
          reason:
              'Step 4 failed: bootstrap-backed JQL Search rows were not visible during hydration. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          _loadingSearchRowLabels(
            screen.visibleIssueSearchResultLabelsSnapshot(),
          ),
          equals([
            for (final label in bootstrapVisibleLabels) '$label Loading...',
          ]),
          reason:
              'Step 4 failed: bootstrap-backed rows did not expose the expected in-place loading indicators while hydration was pending. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isIssueSearchResultTextVisible(
            'TRACK-401',
            'Highest priority bootstrap alpha',
            'To Do',
          ),
          isTrue,
          reason:
              'Step 4 failed: the first bootstrap-backed search row did not keep its visible status text while hydration was pending. '
              'Visible row texts: ${_formatSnapshot(screen.issueSearchResultTextsSnapshot('TRACK-401', 'Highest priority bootstrap alpha'))}.',
        );
        expect(
          await screen.isTextVisible(firstPageSummary),
          isFalse,
          reason:
              'Step 4 failed: the paginated hydrated summary appeared before the async search request completed.',
        );

        await screen.waitWithoutInteraction(
          _Ts451SearchHydrationRepository.searchDelay +
              const Duration(milliseconds: 300),
        );

        expect(
          await screen.isSemanticsLabelVisible('JQL Search Loading...'),
          isFalse,
          reason:
              'Expected result failed: the in-place JQL Search loading banner remained visible after hydration completed.',
        );
        expect(
          _baseSearchRowLabels(screen.visibleIssueSearchResultLabelsSnapshot()),
          equals(bootstrapVisibleLabels),
          reason:
              'Expected result failed: the visible first-page rows changed after hydration instead of staying in place. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          _loadingSearchRowLabels(
            screen.visibleIssueSearchResultLabelsSnapshot(),
          ),
          isEmpty,
          reason:
              'Expected result failed: per-row loading indicators were still visible after hydration completed. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(firstPageSummary),
          isTrue,
          reason:
              'Expected result failed: the hydrated JQL Search page did not show the visible "$firstPageSummary" summary in place.',
        );
        expect(
          await screen.isTextVisible('Load more'),
          isTrue,
          reason:
              'Human-style verification failed: after hydration completed, the user-facing JQL Search panel did not expose the visible "Load more" control for the remaining results.',
        );
        expect(
          find.byType(CircularProgressIndicator),
          findsNothing,
          reason:
              'Human-style verification failed: a blocking spinner was still visible after the search hydration completed.',
        );
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
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

List<String> _baseSearchRowLabels(List<String> labels) {
  return [
    for (final label in labels)
      if (!label.endsWith(' Loading...')) label,
  ];
}

List<String> _loadingSearchRowLabels(List<String> labels) {
  return [
    for (final label in labels)
      if (label.endsWith(' Loading...')) label,
  ];
}

class _Ts451SearchHydrationRepository extends DemoTrackStateRepository {
  _Ts451SearchHydrationRepository();

  static const Duration searchDelay = Duration(seconds: 5);
  static const JqlSearchService _searchService = JqlSearchService();

  int searchRequests = 0;

  static final List<TrackStateIssue> _issues = <TrackStateIssue>[
    _Ts451IssueFactory.issue(
      key: 'TRACK-401',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Highest priority bootstrap alpha',
      status: IssueStatus.todo,
      statusId: 'todo',
    ),
    _Ts451IssueFactory.issue(
      key: 'TRACK-402',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Highest priority bootstrap beta',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
    ),
    _Ts451IssueFactory.issue(
      key: 'TRACK-403',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'High priority visible partial row',
      status: IssueStatus.todo,
      statusId: 'todo',
    ),
    _Ts451IssueFactory.issue(
      key: 'TRACK-404',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'High priority non-blocking list shell',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
    ),
    _Ts451IssueFactory.issue(
      key: 'TRACK-405',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority hydration placeholder',
      status: IssueStatus.todo,
      statusId: 'todo',
    ),
    _Ts451IssueFactory.issue(
      key: 'TRACK-406',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority in-place completion',
      status: IssueStatus.inProgress,
      statusId: 'in-progress',
    ),
    _Ts451IssueFactory.issue(
      key: 'TRACK-407',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Low priority second page continuity',
      status: IssueStatus.todo,
      statusId: 'todo',
    ),
    _Ts451IssueFactory.issue(
      key: 'TRACK-408',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Low priority trailing hydrated row',
      status: IssueStatus.inReview,
      statusId: 'in-review',
    ),
  ];

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await super.loadSnapshot();
    return TrackerSnapshot(project: snapshot.project, issues: _issues);
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    searchRequests += 1;
    await Future<void>.delayed(searchDelay);
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
}

abstract final class _Ts451IssueFactory {
  static TrackStateIssue issue({
    required String key,
    required IssuePriority priority,
    required String priorityId,
    required String summary,
    required IssueStatus status,
    required String statusId,
  }) {
    return TrackStateIssue(
      key: key,
      project: 'TRACK',
      issueType: IssueType.task,
      issueTypeId: 'task',
      status: status,
      statusId: statusId,
      priority: priority,
      priorityId: priorityId,
      summary: summary,
      description: '$summary description.',
      assignee: 'Taylor QA',
      reporter: 'Taylor QA',
      labels: const <String>['search', 'hydration'],
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
      acceptanceCriteria: const <String>[],
      comments: const <IssueComment>[],
      links: const <IssueLink>[],
      attachments: const <IssueAttachment>[],
      isArchived: false,
    );
  }
}
