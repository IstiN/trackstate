import '../../domain/models/trackstate_models.dart';

abstract interface class TrackStateRepository {
  Future<TrackerSnapshot> loadSnapshot();
  Future<List<TrackStateIssue>> searchIssues(String jql);
}

class DemoTrackStateRepository implements TrackStateRepository {
  const DemoTrackStateRepository();

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async {
    final query = jql.trim().toLowerCase();
    final issues = _snapshot.issues;
    if (query.isEmpty) return issues;

    Iterable<TrackStateIssue> results = issues;
    if (query.contains('status != done')) {
      results = results.where((issue) => issue.status != IssueStatus.done);
    }
    if (query.contains('status = done')) {
      results = results.where((issue) => issue.status == IssueStatus.done);
    }
    if (query.contains('issuetype = story') ||
        query.contains('issuetype = "story"') ||
        query.contains('issuetype = story')) {
      results = results.where((issue) => issue.issueType == IssueType.story);
    }
    final keyMatch = RegExp(
      r'(?:epic|parent)\s*=\s*([a-z]+-\d+)',
    ).firstMatch(query);
    if (keyMatch != null) {
      final key = keyMatch.group(1)!.toUpperCase();
      results = results.where(
        (issue) => issue.epicKey == key || issue.parentKey == key,
      );
    }
    final freeText = query
        .replaceAll(RegExp(r'project\s*=\s*[a-z]+'), '')
        .replaceAll(RegExp(r'status\s*(!=|=)\s*[a-z ]+'), '')
        .replaceAll(RegExp(r'issuetype\s*=\s*"?[a-z -]+"?'), '')
        .replaceAll(RegExp(r'(?:epic|parent)\s*=\s*[a-z]+-\d+'), '')
        .replaceAll(RegExp(r'order\s+by.+$'), '')
        .replaceAll(RegExp(r'\b(and|or)\b'), '')
        .trim();
    if (freeText.isNotEmpty && !freeText.contains('=')) {
      results = results.where(
        (issue) =>
            issue.summary.toLowerCase().contains(freeText) ||
            issue.key.toLowerCase().contains(freeText),
      );
    }
    final sorted = results.toList()
      ..sort(
        (a, b) =>
            _priorityRank(b.priority).compareTo(_priorityRank(a.priority)),
      );
    return sorted;
  }
}

int _priorityRank(IssuePriority priority) => switch (priority) {
  IssuePriority.highest => 4,
  IssuePriority.high => 3,
  IssuePriority.medium => 2,
  IssuePriority.low => 1,
};

const _repositoryName = String.fromEnvironment(
  'TRACKSTATE_REPOSITORY',
  defaultValue: 'trackstate/trackstate',
);
const _sourceRef = String.fromEnvironment(
  'TRACKSTATE_SOURCE_REF',
  defaultValue: 'main',
);

const _project = ProjectConfig(
  key: 'TRACK',
  name: 'TrackState.AI',
  repository: _repositoryName,
  branch: _sourceRef,
  issueTypes: ['Epic', 'Story', 'Task', 'Sub-task', 'Bug'],
  statuses: ['To Do', 'In Progress', 'In Review', 'Done'],
  fields: [
    'Summary',
    'Description',
    'Acceptance Criteria',
    'Priority',
    'Assignee',
    'Labels',
    'Components',
    'Fix Versions',
  ],
);

const _snapshot = TrackerSnapshot(
  project: _project,
  issues: [
    TrackStateIssue(
      key: 'TRACK-1',
      project: 'TRACK',
      issueType: IssueType.epic,
      status: IssueStatus.inProgress,
      priority: IssuePriority.highest,
      summary: 'Platform Foundation',
      description:
          'Bootstrap the Git-native Jira-compatible tracker with provider abstractions, repository-backed storage, and a polished Flutter client.',
      assignee: 'Ana',
      reporter: 'Uladzimir',
      labels: ['mvp', 'git-native'],
      components: ['tracker-core'],
      parentKey: null,
      epicKey: null,
      progress: .62,
      updatedLabel: '2 minutes ago',
      acceptanceCriteria: [
        'Issue metadata follows canonical frontmatter.',
        'JQL filters work without a backend service.',
        'Git history remains the audit trail.',
      ],
      comments: [
        IssueComment(
          author: 'Priya',
          body: 'Repository fixture is ready for visual and functional tests.',
          updatedLabel: '2m ago',
        ),
      ],
    ),
    TrackStateIssue(
      key: 'TRACK-12',
      project: 'TRACK',
      issueType: IssueType.story,
      status: IssueStatus.inProgress,
      priority: IssuePriority.high,
      summary: 'Implement Git sync service',
      description:
          'Create a replaceable storage adapter so local Git commands and hosted provider APIs read and write the same tracker files.',
      assignee: 'Denis',
      reporter: 'Ana',
      labels: ['sync', 'provider'],
      components: ['storage'],
      parentKey: null,
      epicKey: 'TRACK-1',
      progress: .44,
      updatedLabel: '5 minutes ago',
      acceptanceCriteria: [
        'Detect changes in the repository.',
        'Fetch new commits and map to issues.',
        'Push issue updates as commits.',
        'Handle merge conflicts gracefully.',
      ],
      comments: [
        IssueComment(
          author: 'Maria',
          body: 'Conflict wording should be explicit and never success-shaped.',
          updatedLabel: 'now',
        ),
        IssueComment(
          author: 'Noah',
          body: 'Keep GitHub API types behind the provider interface.',
          updatedLabel: '1h ago',
        ),
      ],
    ),
    TrackStateIssue(
      key: 'TRACK-17',
      project: 'TRACK',
      issueType: IssueType.story,
      status: IssueStatus.inReview,
      priority: IssuePriority.high,
      summary: 'Implement OAuth flow',
      description:
          'Authorize users through their repository permissions without requiring a backend server for the fork-and-run experience.',
      assignee: 'Maria',
      reporter: 'Uladzimir',
      labels: ['auth', 'github'],
      components: ['provider-github'],
      parentKey: null,
      epicKey: 'TRACK-1',
      progress: .85,
      updatedLabel: 'Jun 10',
      acceptanceCriteria: [
        'PAT/OAuth path works for GitHub Pages.',
        'Collaborator permissions are surfaced in UI.',
        'Provider interface remains replaceable.',
      ],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-21',
      project: 'TRACK',
      issueType: IssueType.task,
      status: IssueStatus.todo,
      priority: IssuePriority.medium,
      summary: 'Create API docs',
      description:
          'Document provider interfaces, storage layout, JQL behavior, and CLI JSON compatibility.',
      assignee: 'Liam',
      reporter: 'Ana',
      labels: ['docs'],
      components: ['developer-experience'],
      parentKey: null,
      epicKey: 'TRACK-1',
      progress: .18,
      updatedLabel: 'May 20',
      acceptanceCriteria: ['Docs link to repository examples.'],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-25',
      project: 'TRACK',
      issueType: IssueType.subtask,
      status: IssueStatus.todo,
      priority: IssuePriority.medium,
      summary: 'Add unit tests',
      description: 'Cover storage transforms, JQL filtering, and view models.',
      assignee: 'Emma',
      reporter: 'Denis',
      labels: ['tests'],
      components: ['quality'],
      parentKey: 'TRACK-12',
      epicKey: 'TRACK-1',
      progress: .22,
      updatedLabel: '1h ago',
      acceptanceCriteria: ['Tests run in GitHub Actions.'],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-29',
      project: 'TRACK',
      issueType: IssueType.story,
      status: IssueStatus.done,
      priority: IssuePriority.low,
      summary: 'Wire integration tests for Git sync',
      description: 'Provide permanent tests for core issue workflows.',
      assignee: 'Priya',
      reporter: 'Ana',
      labels: ['automation'],
      components: ['quality'],
      parentKey: null,
      epicKey: 'TRACK-1',
      progress: 1,
      updatedLabel: 'Jun 20',
      acceptanceCriteria: ['Happy path and conflict path are covered.'],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-34',
      project: 'TRACK',
      issueType: IssueType.epic,
      status: IssueStatus.inProgress,
      priority: IssuePriority.medium,
      summary: 'Mobile Experience',
      description:
          'Deliver responsive layouts and touch-optimized screens for issue triage.',
      assignee: 'Noah',
      reporter: 'Uladzimir',
      labels: ['mobile', 'responsive'],
      components: ['flutter-ui'],
      parentKey: null,
      epicKey: null,
      progress: .37,
      updatedLabel: 'Jun 8',
      acceptanceCriteria: [
        'Mobile view keeps primary actions reachable.',
        'Semantics labels cover navigation and issue actions.',
      ],
      comments: [],
    ),
    TrackStateIssue(
      key: 'TRACK-41',
      project: 'TRACK',
      issueType: IssueType.story,
      status: IssueStatus.todo,
      priority: IssuePriority.low,
      summary: 'Design mobile navigation',
      description:
          'Adapt the sidebar/content model into a compact bottom navigation flow.',
      assignee: 'Priya',
      reporter: 'Noah',
      labels: ['mobile'],
      components: ['flutter-ui'],
      parentKey: null,
      epicKey: 'TRACK-34',
      progress: .12,
      updatedLabel: 'May 29',
      acceptanceCriteria: ['No overflow at narrow widths.'],
      comments: [],
    ),
  ],
);
