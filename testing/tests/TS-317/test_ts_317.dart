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
    'TS-317 appends JQL Search results and preserves the active query state',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const query = 'project = TRACK ORDER BY priority DESC, key ASC';
      const firstPageSummary = 'Showing 6 of 12 issues';
      const issueLabels = <String>[
        'Open TRACK-101 Highest priority pagination baseline',
        'Open TRACK-102 Highest priority pagination follow-up',
        'Open TRACK-103 Highest priority pagination polish',
        'Open TRACK-104 High priority load more visibility',
        'Open TRACK-105 High priority query persistence',
        'Open TRACK-106 High priority appended ordering',
        'Open TRACK-107 Medium priority second page first row',
        'Open TRACK-108 Medium priority second page second row',
        'Open TRACK-109 Medium priority second page third row',
        'Open TRACK-110 Low priority final page first row',
        'Open TRACK-111 Low priority final page second row',
        'Open TRACK-112 Low priority final page third row',
      ];

      try {
        await screen.pump(const _Ts317PaginatedSearchRepository());
        screen.expectLocalRuntimeChrome();

        await screen.openSection('JQL Search');
        await screen.searchIssues(query);

        expect(
          await screen.readLabeledTextFieldValue('Search issues'),
          query,
          reason:
              'Step 1 failed: the JQL Search bar did not keep the exact query '
              'the user submitted.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot(),
          equals(issueLabels.take(6).toList()),
          reason:
              'Step 1 failed: JQL Search did not render the expected first page '
              'of ordered results. Visible issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(firstPageSummary),
          isTrue,
          reason:
              'Step 1 failed: the JQL Search panel did not show the visible '
              '"$firstPageSummary" pagination summary.',
        );
        expect(
          await screen.isTextVisible('Load more'),
          isTrue,
          reason:
              'Step 2 failed: the first page did not expose a visible '
              '"Load more" control before the last page was reached.',
        );
        expect(
          await screen.isSemanticsLabelVisible('Load more issues'),
          isTrue,
          reason:
              'Step 2 failed: the visible "Load more" control did not expose '
              'the expected screen-reader label.',
        );

        final loadMoreTapped = await screen.tapVisibleControl('Load more');
        expect(
          loadMoreTapped,
          isTrue,
          reason:
              'Step 2 failed: the visible "Load more" control could not be '
              'activated from the JQL Search panel.',
        );

        expect(
          await screen.readLabeledTextFieldValue('Search issues'),
          query,
          reason:
              'Step 3 failed: after appending results, the JQL Search bar no '
              'longer showed the same query and sort string.',
        );
        expect(
          screen.visibleIssueSearchResultLabelsSnapshot(),
          equals(issueLabels),
          reason:
              'Step 3 failed: tapping "Load more" did not append the next page '
              'after the original results in the same visible order. Visible '
              'issue rows: '
              '${_formatSnapshot(screen.visibleIssueSearchResultLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(firstPageSummary),
          isFalse,
          reason:
              'Step 3 failed: the first-page summary remained visible after all '
              'matching issues were loaded.',
        );
        expect(
          await screen.isTextVisible('Load more'),
          isFalse,
          reason:
              'Step 4 failed: the final page still rendered a visible '
              '"Load more" control even though all matching issues were already '
              'shown.',
        );
        expect(
          await screen.isSemanticsLabelVisible('Load more issues'),
          isFalse,
          reason:
              'Step 4 failed: the final page still exposed the "Load more" '
              'screen-reader control after the last page was reached.',
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

class _Ts317PaginatedSearchRepository implements TrackStateRepository {
  const _Ts317PaginatedSearchRepository();

  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const JqlSearchService _searchService = JqlSearchService();

  static final List<TrackStateIssue> _issues = <TrackStateIssue>[
    _Ts317IssueFactory.issue(
      key: 'TRACK-101',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Highest priority pagination baseline',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-102',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Highest priority pagination follow-up',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-103',
      priority: IssuePriority.highest,
      priorityId: 'highest',
      summary: 'Highest priority pagination polish',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-104',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'High priority load more visibility',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-105',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'High priority query persistence',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-106',
      priority: IssuePriority.high,
      priorityId: 'high',
      summary: 'High priority appended ordering',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-107',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority second page first row',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-108',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority second page second row',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-109',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Medium priority second page third row',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-110',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Low priority final page first row',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-111',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Low priority final page second row',
    ),
    _Ts317IssueFactory.issue(
      key: 'TRACK-112',
      priority: IssuePriority.low,
      priorityId: 'low',
      summary: 'Low priority final page third row',
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
        'TS-317 pagination fixture is read-only.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'TS-317 pagination fixture is read-only.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw const TrackStateRepositoryException(
      'TS-317 pagination fixture does not create issues.',
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

abstract final class _Ts317IssueFactory {
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
      labels: const <String>['pagination'],
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
