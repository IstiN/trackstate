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
    'TS-316 keeps JQL Search ordering deterministic with key-based tie-breaking',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const defaultQuery = 'project = TRACK';
      const priorityQuery = 'project = TRACK ORDER BY priority DESC';
      const firstPageSummary = 'Showing 6 of 10 issues';
      const defaultOrderedLabels = <String>[
        'Open TRACK-5 High priority alpha boundary',
        'Open TRACK-7 High priority beta boundary',
        'Open TRACK-10 Medium priority first tie result',
        'Open TRACK-12 Medium priority second tie result',
        'Open TRACK-14 Medium priority third tie result',
        'Open TRACK-16 Medium priority fourth tie result',
        'Open TRACK-30 Highest priority alpha boundary',
        'Open TRACK-31 Highest priority beta boundary',
        'Open TRACK-100 Low priority alpha boundary',
        'Open TRACK-101 Low priority beta boundary',
      ];
      const priorityOrderedLabels = <String>[
        'Open TRACK-30 Highest priority alpha boundary',
        'Open TRACK-31 Highest priority beta boundary',
        'Open TRACK-5 High priority alpha boundary',
        'Open TRACK-7 High priority beta boundary',
        'Open TRACK-10 Medium priority first tie result',
        'Open TRACK-12 Medium priority second tie result',
        'Open TRACK-14 Medium priority third tie result',
        'Open TRACK-16 Medium priority fourth tie result',
        'Open TRACK-100 Low priority alpha boundary',
        'Open TRACK-101 Low priority beta boundary',
      ];

      try {
        await screen.pump(const _Ts316DeterministicOrderingRepository());
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');

        await screen.searchIssues(defaultQuery);

        expect(
          await screen.readJqlSearchFieldValue(),
          defaultQuery,
          reason:
              'Step 1 failed: the JQL Search field did not keep the exact '
              'query without ORDER BY that the user submitted.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot(),
          equals(defaultOrderedLabels.take(6).toList()),
          reason:
              'Step 1 failed: without ORDER BY, JQL Search did not render the '
              'first page in issue-key ascending order. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(firstPageSummary),
          isTrue,
          reason:
              'Step 1 failed: the visible JQL Search results did not show the '
              '"$firstPageSummary" pagination summary.',
        );
        expect(
          await screen.isTextVisible('Load more'),
          isTrue,
          reason:
              'Step 1 failed: the user-facing JQL Search panel did not expose '
              'a visible "Load more" control for the remaining default-sort '
              'results.',
        );

        final defaultLoadMoreTapped = await screen.tapVisibleControl(
          'Load more',
        );
        expect(
          defaultLoadMoreTapped,
          isTrue,
          reason:
              'Step 1 failed: the visible "Load more" control for the default '
              'JQL ordering could not be activated.',
        );
        expect(
          await screen.readJqlSearchFieldValue(),
          defaultQuery,
          reason:
              'Step 1 failed: after loading the second default-sort page, the '
              'JQL Search field no longer showed the original query.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot(),
          equals(defaultOrderedLabels),
          reason:
              'Step 1 failed: the second default-sort page did not continue '
              'from the previous issue key boundary in stable ascending order. '
              'Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible('Load more'),
          isFalse,
          reason:
              'Step 1 failed: after all default-sort results were visible, the '
              'JQL Search panel still showed a "Load more" control.',
        );

        await screen.pump(const _Ts316DeterministicOrderingRepository());
        screen.expectLocalRuntimeChrome();
        await screen.openSection('JQL Search');
        await screen.searchIssues(priorityQuery);

        expect(
          await screen.readJqlSearchFieldValue(),
          priorityQuery,
          reason:
              'Step 2 failed: the JQL Search field did not keep the exact '
              'priority sort query that the user submitted.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot(),
          equals(priorityOrderedLabels.take(6).toList()),
          reason:
              'Step 2 failed: ORDER BY priority DESC did not keep same-priority '
              'issues sorted by key ascending on the first page. Visible issue '
              'rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(firstPageSummary),
          isTrue,
          reason:
              'Step 2 failed: the sorted JQL Search results did not show the '
              '"$firstPageSummary" pagination summary.',
        );
        expect(
          await screen.isTextVisible('Load more'),
          isTrue,
          reason:
              'Step 2 failed: the sorted JQL Search results did not expose a '
              'visible "Load more" control before the tie group crossed onto '
              'the next page.',
        );

        final priorityLoadMoreTapped = await screen.tapVisibleControl(
          'Load more',
        );
        expect(
          priorityLoadMoreTapped,
          isTrue,
          reason:
              'Step 3 failed: the visible "Load more" control for the sorted '
              'JQL results could not be activated.',
        );
        expect(
          await screen.readJqlSearchFieldValue(),
          priorityQuery,
          reason:
              'Step 3 failed: after loading the next sorted page, the JQL '
              'Search field no longer showed the submitted ORDER BY query.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot(),
          equals(priorityOrderedLabels),
          reason:
              'Step 3 failed: equal-priority issues did not preserve key '
              'ascending order across the page boundary, so pagination was not '
              'stable between requests. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible('Load more'),
          isFalse,
          reason:
              'Step 3 failed: after the final sorted page was appended, the '
              'JQL Search panel still exposed a visible "Load more" control.',
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

class _Ts316DeterministicOrderingRepository implements TrackStateRepository {
  const _Ts316DeterministicOrderingRepository();

  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const JqlSearchService _searchService = JqlSearchService();

  static final List<TrackStateIssue> _issues = <TrackStateIssue>[
    _Ts316IssueFactory.issue(
      key: 'TRACK-100',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Low priority alpha boundary',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-31',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Highest priority beta boundary',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-12',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority second tie result',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-5',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'High priority alpha boundary',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-30',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Highest priority alpha boundary',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-16',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority fourth tie result',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-101',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Low priority beta boundary',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-7',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'High priority beta boundary',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-14',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority third tie result',
    ),
    _Ts316IssueFactory.issue(
      key: 'TRACK-10',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority first tie result',
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
        'TS-316 ordering fixture is read-only.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'TS-316 ordering fixture is read-only.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw const TrackStateRepositoryException(
      'TS-316 ordering fixture does not create issues.',
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

abstract final class _Ts316IssueFactory {
  static const String _projectKey = 'TRACK';
  static const String _issueTypeId = 'task';
  static const String _statusId = 'todo';

  static TrackStateIssue issue({
    required String key,
    required IssuePriority priority,
    required String priorityId,
    required String summary,
  }) {
    return TrackStateIssue(
      key: key,
      project: _projectKey,
      issueType: IssueType.task,
      issueTypeId: _issueTypeId,
      status: IssueStatus.todo,
      statusId: _statusId,
      priority: priority,
      priorityId: priorityId,
      summary: summary,
      description: '$summary description.',
      assignee: 'Taylor QA',
      reporter: 'Taylor QA',
      labels: const <String>['pagination', 'deterministic-ordering'],
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
