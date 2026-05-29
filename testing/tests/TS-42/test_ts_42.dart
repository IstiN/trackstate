import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  testWidgets(
    'TS-42: direct nested issue route shows TRACK-3 as the primary issue identity',
    (tester) async {
      final semantics = tester.ensureSemantics();
      addTearDown(semantics.dispose);

      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      tester.binding.platformDispatcher.defaultRouteNameTestValue =
          '/issues/TRACK-3';
      addTearDown(
        tester.binding.platformDispatcher.clearDefaultRouteNameTestValue,
      );

      await tester.pumpWidget(
        const TrackStateApp(repository: _Ts42NestedIssueRepository()),
      );
      await _pumpUntilLoaded(tester);

      final expectedIssueDetail = find.bySemanticsLabel('Issue detail TRACK-3');
      final observedIssueDetails = _matchingSemanticsLabels(
        tester,
        RegExp(r'^Issue detail '),
      );
      final visibleTexts = _visibleTextSnippets(tester);

      expect(
        expectedIssueDetail,
        findsOneWidget,
        reason:
            'Opening /issues/TRACK-3 should render the TRACK-3 issue detail '
            'surface after loading completes. Instead the app showed issue '
            'detail labels $observedIssueDetails with visible text snippets '
            '$visibleTexts.',
      );

      expect(
        find.text('TRACK-3'),
        findsWidgets,
        reason:
            'The requested nested issue key should be visible on the loaded '
            'detail surface for /issues/TRACK-3.',
      );
    },
  );
}

class _Ts42NestedIssueRepository implements TrackStateRepository {
  const _Ts42NestedIssueRepository();

  static const _project = ProjectConfig(
    key: 'TRACK',
    name: 'TrackState Demo',
    repository: 'trackstate/trackstate',
    branch: 'main',
    defaultLocale: 'en',
    issueTypeDefinitions: [
      TrackStateConfigEntry(id: 'epic', name: 'Epic'),
      TrackStateConfigEntry(id: 'story', name: 'Story'),
      TrackStateConfigEntry(id: 'subtask', name: 'Sub-task'),
    ],
    statusDefinitions: [
      TrackStateConfigEntry(id: 'todo', name: 'To Do'),
      TrackStateConfigEntry(id: 'inProgress', name: 'In Progress'),
      TrackStateConfigEntry(id: 'done', name: 'Done'),
    ],
    fieldDefinitions: [
      TrackStateFieldDefinition(
        id: 'summary',
        name: 'Summary',
        type: 'string',
        required: true,
      ),
      TrackStateFieldDefinition(
        id: 'description',
        name: 'Description',
        type: 'markdown',
        required: false,
      ),
      TrackStateFieldDefinition(
        id: 'acceptanceCriteria',
        name: 'Acceptance Criteria',
        type: 'markdown-list',
        required: false,
      ),
    ],
  );

  static const _issues = [
    TrackStateIssue(
      key: 'TRACK-1',
      project: 'TRACK',
      issueType: IssueType.epic,
      issueTypeId: 'epic',
      status: IssueStatus.inProgress,
      statusId: 'inProgress',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Build TrackState.AI MVP',
      description: 'Create the first usable TrackState.AI experience.',
      assignee: 'route-tester',
      reporter: 'route-tester',
      labels: [],
      components: [],
      fixVersionIds: [],
      watchers: [],
      customFields: {},
      parentKey: null,
      epicKey: null,
      parentPath: null,
      epicPath: null,
      progress: 0.5,
      updatedLabel: '1 hour ago',
      acceptanceCriteria: [],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
      storagePath: 'TRACK/TRACK-1/main.md',
    ),
    TrackStateIssue(
      key: 'TRACK-2',
      project: 'TRACK',
      issueType: IssueType.story,
      issueTypeId: 'story',
      status: IssueStatus.todo,
      statusId: 'todo',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Implement JQL parser',
      description: 'Make search work with Jira-compatible filters.',
      assignee: 'route-tester',
      reporter: 'route-tester',
      labels: [],
      components: [],
      fixVersionIds: [],
      watchers: [],
      customFields: {},
      updatedLabel: '30 minutes ago',
      storagePath: 'TRACK/TRACK-1/TRACK-2/main.md',
      parentKey: 'TRACK-1',
      parentPath: 'TRACK/TRACK-1/main.md',
      epicKey: 'TRACK-1',
      epicPath: 'TRACK/TRACK-1/main.md',
      progress: 0.25,
      acceptanceCriteria: [],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
    ),
    TrackStateIssue(
      key: 'TRACK-3',
      project: 'TRACK',
      issueType: IssueType.subtask,
      issueTypeId: 'subtask',
      status: IssueStatus.todo,
      statusId: 'todo',
      priority: IssuePriority.medium,
      priorityId: 'medium',
      summary: 'Parse ORDER BY clause',
      description: 'Support ORDER BY fields in nested issue queries.',
      assignee: 'route-tester',
      reporter: 'route-tester',
      labels: [],
      components: [],
      fixVersionIds: [],
      watchers: [],
      customFields: {},
      updatedLabel: 'just now',
      storagePath: 'TRACK/TRACK-1/TRACK-2/TRACK-3/main.md',
      parentKey: 'TRACK-2',
      parentPath: 'TRACK/TRACK-1/TRACK-2/main.md',
      epicKey: 'TRACK-1',
      epicPath: 'TRACK/TRACK-1/main.md',
      progress: 0,
      acceptanceCriteria: ['Render pagination controls with stable ordering.'],
      comments: [],
      links: [],
      attachments: [],
      isArchived: false,
    ),
  ];

  static const _index = RepositoryIndex(
    entries: [
      RepositoryIssueIndexEntry(
        key: 'TRACK-1',
        path: 'TRACK/TRACK-1/main.md',
        childKeys: ['TRACK-2'],
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-2',
        path: 'TRACK/TRACK-1/TRACK-2/main.md',
        childKeys: ['TRACK-3'],
        parentKey: 'TRACK-1',
        parentPath: 'TRACK/TRACK-1/main.md',
        epicKey: 'TRACK-1',
        epicPath: 'TRACK/TRACK-1/main.md',
      ),
      RepositoryIssueIndexEntry(
        key: 'TRACK-3',
        path: 'TRACK/TRACK-1/TRACK-2/TRACK-3/main.md',
        childKeys: [],
        parentKey: 'TRACK-2',
        parentPath: 'TRACK/TRACK-1/TRACK-2/main.md',
        epicKey: 'TRACK-1',
        epicPath: 'TRACK/TRACK-1/main.md',
      ),
    ],
  );

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'route-tester', displayName: 'Route Tester');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => const TrackerSnapshot(
    project: _project,
    issues: _issues,
    repositoryIndex: _index,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async {
    final query = jql.trim().toLowerCase();
    if (query.isEmpty) {
      return _issues;
    }
    return _issues.where((issue) {
      final haystack = '${issue.key} ${issue.summary}'.toLowerCase();
      return haystack.contains(query);
    }).toList();
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async => issue.copyWith(description: description.trim());

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, statusId: status.id);
}

Future<void> _pumpUntilLoaded(
  WidgetTester tester, {
  Duration timeout = const Duration(seconds: 10),
}) async {
  final end = DateTime.now().add(timeout);

  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 100));

    final loadingVisible = find
        .byType(CircularProgressIndicator)
        .evaluate()
        .isNotEmpty;
    final routeResolved =
        find
            .bySemanticsLabel(RegExp(r'^Issue detail '))
            .evaluate()
            .isNotEmpty ||
        find.text('Dashboard').evaluate().isNotEmpty ||
        find.text('JQL Search').evaluate().isNotEmpty ||
        find.text('Hierarchy').evaluate().isNotEmpty;

    if (!loadingVisible && routeResolved) {
      await tester.pump(const Duration(milliseconds: 300));
      return;
    }
  }

  fail(
    'Timed out waiting for the app to finish loading /issues/TRACK-3. '
    'Observed text snippets: ${_visibleTextSnippets(tester)}',
  );
}

List<String> _matchingSemanticsLabels(WidgetTester tester, Pattern pattern) {
  return find
      .byWidgetPredicate((widget) {
        if (widget is! Semantics) {
          return false;
        }
        final label = widget.properties.label;
        if (label == null) {
          return false;
        }
        if (pattern is RegExp) {
          return pattern.hasMatch(label);
        }
        return label.contains(pattern.toString());
      })
      .evaluate()
      .map((element) => (element.widget as Semantics).properties.label)
      .whereType<String>()
      .toSet()
      .toList()
    ..sort();
}

List<String> _visibleTextSnippets(WidgetTester tester) {
  return find
      .byWidgetPredicate((widget) => widget is Text || widget is SelectableText)
      .evaluate()
      .map((element) {
        final widget = element.widget;
        if (widget is Text) {
          return widget.data ?? widget.textSpan?.toPlainText() ?? '';
        }
        if (widget is SelectableText) {
          return widget.data ?? widget.textSpan?.toPlainText() ?? '';
        }
        return '';
      })
      .map((text) => text.replaceAll(RegExp(r'\s+'), ' ').trim())
      .where((text) => text.isNotEmpty)
      .toSet()
      .toList()
    ..sort()
    ..retainWhere((text) => text.length <= 120);
}
