import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  const service = JqlSearchService();
  const project = ProjectConfig(
    key: 'TRACK',
    name: 'TrackState',
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
      TrackStateConfigEntry(id: 'in-progress', name: 'In Progress'),
      TrackStateConfigEntry(id: 'done', name: 'Done'),
    ],
    fieldDefinitions: [
      TrackStateFieldDefinition(
        id: 'summary',
        name: 'Summary',
        type: 'string',
        required: true,
      ),
    ],
    priorityDefinitions: [
      TrackStateConfigEntry(id: 'highest', name: 'Highest'),
      TrackStateConfigEntry(id: 'high', name: 'High'),
      TrackStateConfigEntry(id: 'medium', name: 'Medium'),
      TrackStateConfigEntry(id: 'low', name: 'Low'),
    ],
  );
  final issues = [
    _issue(
      key: 'TRACK-2',
      summary: 'Implement pagination',
      description: 'Load more support for search results.',
      acceptanceCriteria: const [
        'Append the next page without resetting state.',
      ],
      priority: IssuePriority.high,
      priorityId: 'high',
      assignee: 'ana',
      labels: const ['release'],
      epicKey: 'TRACK-1',
    ),
    _issue(
      key: 'TRACK-3',
      summary: 'Implement parser',
      description: 'Supports quoted values such as "In Progress".',
      acceptanceCriteria: const ['Parse AND clauses.'],
      priority: IssuePriority.high,
      priorityId: 'high',
      labels: const ['ux'],
      epicKey: 'TRACK-1',
    ),
    _issue(
      key: 'TRACK-4',
      summary: 'Write order by tests',
      description: 'Verifies deterministic pagination.',
      acceptanceCriteria: const [
        'Sort by issue key ascending when values tie.',
      ],
      priority: IssuePriority.medium,
      priorityId: 'medium',
      assignee: 'bob',
      parentKey: 'TRACK-2',
      epicKey: 'TRACK-1',
      issueType: IssueType.subtask,
      issueTypeId: 'subtask',
      status: IssueStatus.todo,
      statusId: 'todo',
    ),
    _issue(
      key: 'TRACK-10',
      summary: 'Document search',
      description: 'Same priority as other open stories.',
      acceptanceCriteria: const ['Stay stable across pages.'],
      priority: IssuePriority.high,
      priorityId: 'high',
      assignee: 'zoe',
      labels: const ['release'],
      epicKey: 'TRACK-1',
    ),
    _issue(
      key: 'TRACK-11',
      summary: 'Close completed work',
      description: 'This issue is done.',
      acceptanceCriteria: const ['Remain filterable by status.'],
      priority: IssuePriority.low,
      priorityId: 'low',
      assignee: 'carol',
      epicKey: 'TRACK-1',
      status: IssueStatus.done,
      statusId: 'done',
    ),
  ];

  test('supports quoted values and text search across description fields', () {
    final page = service.search(
      issues: issues,
      project: project,
      jql:
          'project = TRACK AND issueType = "Story" AND status = "In Progress" AND load more',
    );

    expect(page.issues.map((issue) => issue.key), ['TRACK-2']);
    expect(page.total, 1);
  });

  test('supports empty checks and label membership semantics', () {
    final emptyAssignee = service.search(
      issues: issues,
      project: project,
      jql: 'assignee IS EMPTY AND labels != release ORDER BY key ASC',
    );
    final childIssues = service.search(
      issues: issues,
      project: project,
      jql: 'parent IS NOT EMPTY AND epic = TRACK-1',
    );

    expect(emptyAssignee.issues.map((issue) => issue.key), ['TRACK-3']);
    expect(childIssues.issues.map((issue) => issue.key), ['TRACK-4']);
  });

  test('keeps project-plus-free-text compatibility for key lookups', () {
    final page = service.search(
      issues: issues,
      project: project,
      jql: 'project = TRACK TRACK-10',
    );

    expect(page.issues.map((issue) => issue.key), ['TRACK-10']);
  });

  test('returns deterministic offset pagination with key tie-breakers', () {
    final firstPage = service.search(
      issues: issues,
      project: project,
      jql: 'project = TRACK AND status != Done ORDER BY priority DESC',
      maxResults: 2,
    );
    final secondPage = service.search(
      issues: issues,
      project: project,
      jql: 'project = TRACK AND status != Done ORDER BY priority DESC',
      maxResults: 2,
      continuationToken: firstPage.nextPageToken,
    );

    expect(firstPage.issues.map((issue) => issue.key), ['TRACK-2', 'TRACK-3']);
    expect(firstPage.startAt, 0);
    expect(firstPage.total, 4);
    expect(firstPage.nextStartAt, 2);
    expect(firstPage.nextPageToken, 'offset:2');
    expect(secondPage.issues.map((issue) => issue.key), [
      'TRACK-10',
      'TRACK-4',
    ]);
    expect(secondPage.startAt, 2);
    expect(secondPage.hasMore, isFalse);
  });

  test('supports explicit startAt values with natural issue-key ordering', () {
    final page = service.search(
      issues: issues,
      project: project,
      jql: 'project = TRACK ORDER BY key ASC',
      startAt: 1,
      maxResults: 3,
    );

    expect(page.issues.map((issue) => issue.key), [
      'TRACK-3',
      'TRACK-4',
      'TRACK-10',
    ]);
  });

  test('rejects unsupported operators and unknown fields', () {
    expect(
      () => service.search(
        issues: issues,
        project: project,
        jql: 'status IN (Done)',
      ),
      throwsA(isA<JqlSearchException>()),
    );
    expect(
      () => service.search(
        issues: issues,
        project: project,
        jql: 'reporter = ana',
      ),
      throwsA(isA<JqlSearchException>()),
    );
  });
}

TrackStateIssue _issue({
  required String key,
  required String summary,
  required String description,
  required List<String> acceptanceCriteria,
  required IssuePriority priority,
  required String priorityId,
  String assignee = '',
  List<String> labels = const [],
  String? parentKey,
  String? epicKey,
  IssueType issueType = IssueType.story,
  String issueTypeId = 'story',
  IssueStatus status = IssueStatus.inProgress,
  String statusId = 'in-progress',
}) {
  return TrackStateIssue(
    key: key,
    project: 'TRACK',
    issueType: issueType,
    issueTypeId: issueTypeId,
    status: status,
    statusId: statusId,
    priority: priority,
    priorityId: priorityId,
    summary: summary,
    description: description,
    assignee: assignee,
    reporter: 'reporter',
    labels: labels,
    components: const [],
    fixVersionIds: const [],
    watchers: const [],
    customFields: const {},
    parentKey: parentKey,
    epicKey: epicKey,
    parentPath: null,
    epicPath: null,
    progress: 0,
    updatedLabel: 'just now',
    acceptanceCriteria: acceptanceCriteria,
    comments: const [],
    links: const [],
    attachments: const [],
    isArchived: false,
    storagePath: 'TRACK/$key/main.md',
    rawMarkdown: '',
  );
}
