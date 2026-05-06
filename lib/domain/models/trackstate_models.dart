enum IssueType { epic, story, task, subtask, bug }

enum IssueStatus { todo, inProgress, inReview, done }

enum IssuePriority { highest, high, medium, low }

class TrackStateIssue {
  const TrackStateIssue({
    required this.key,
    required this.project,
    required this.issueType,
    required this.status,
    required this.priority,
    required this.summary,
    required this.description,
    required this.assignee,
    required this.reporter,
    required this.labels,
    required this.components,
    required this.parentKey,
    required this.epicKey,
    required this.progress,
    required this.updatedLabel,
    required this.acceptanceCriteria,
    required this.comments,
    this.storagePath = '',
    this.rawMarkdown = '',
  });

  final String key;
  final String project;
  final IssueType issueType;
  final IssueStatus status;
  final IssuePriority priority;
  final String summary;
  final String description;
  final String assignee;
  final String reporter;
  final List<String> labels;
  final List<String> components;
  final String? parentKey;
  final String? epicKey;
  final double progress;
  final String updatedLabel;
  final List<String> acceptanceCriteria;
  final List<IssueComment> comments;
  final String storagePath;
  final String rawMarkdown;

  bool get isEpic => issueType == IssueType.epic;

  TrackStateIssue copyWith({
    IssueStatus? status,
    String? rawMarkdown,
    String? updatedLabel,
  }) {
    return TrackStateIssue(
      key: key,
      project: project,
      issueType: issueType,
      status: status ?? this.status,
      priority: priority,
      summary: summary,
      description: description,
      assignee: assignee,
      reporter: reporter,
      labels: labels,
      components: components,
      parentKey: parentKey,
      epicKey: epicKey,
      progress: progress,
      updatedLabel: updatedLabel ?? this.updatedLabel,
      acceptanceCriteria: acceptanceCriteria,
      comments: comments,
      storagePath: storagePath,
      rawMarkdown: rawMarkdown ?? this.rawMarkdown,
    );
  }
}

class IssueComment {
  const IssueComment({
    required this.author,
    required this.body,
    required this.updatedLabel,
  });

  final String author;
  final String body;
  final String updatedLabel;
}

class ProjectConfig {
  const ProjectConfig({
    required this.key,
    required this.name,
    required this.repository,
    required this.branch,
    required this.issueTypes,
    required this.statuses,
    required this.fields,
  });

  final String key;
  final String name;
  final String repository;
  final String branch;
  final List<String> issueTypes;
  final List<String> statuses;
  final List<String> fields;
}

class TrackerSnapshot {
  const TrackerSnapshot({required this.project, required this.issues});

  final ProjectConfig project;
  final List<TrackStateIssue> issues;

  List<TrackStateIssue> get epics =>
      issues.where((issue) => issue.issueType == IssueType.epic).toList();

  List<TrackStateIssue> childrenOf(String key) => issues
      .where((issue) => issue.parentKey == key || issue.epicKey == key)
      .toList();
}

class RepositoryConnection {
  const RepositoryConnection({
    required this.repository,
    required this.branch,
    required this.token,
  });

  final String repository;
  final String branch;
  final String token;
}

class GitHubConnection extends RepositoryConnection {
  const GitHubConnection({
    required super.repository,
    required super.branch,
    required super.token,
  });
}

class RepositoryUser {
  const RepositoryUser({required this.login, required this.displayName});

  final String login;
  final String displayName;

  String get initials {
    final source = displayName.trim().isNotEmpty ? displayName : login;
    final parts = source
        .split(RegExp(r'[\s._-]+'))
        .where((part) => part.isNotEmpty)
        .toList();
    if (parts.isEmpty) return 'GH';
    return parts.take(2).map((part) => part[0].toUpperCase()).join();
  }
}

class GitHubUser extends RepositoryUser {
  const GitHubUser({required super.login, required super.displayName});
}

extension IssueTypeLabel on IssueType {
  String get label => switch (this) {
    IssueType.epic => 'Epic',
    IssueType.story => 'Story',
    IssueType.task => 'Task',
    IssueType.subtask => 'Sub-task',
    IssueType.bug => 'Bug',
  };
}

extension IssueStatusLabel on IssueStatus {
  String get label => switch (this) {
    IssueStatus.todo => 'To Do',
    IssueStatus.inProgress => 'In Progress',
    IssueStatus.inReview => 'In Review',
    IssueStatus.done => 'Done',
  };
}

extension IssuePriorityLabel on IssuePriority {
  String get label => switch (this) {
    IssuePriority.highest => 'Highest',
    IssuePriority.high => 'High',
    IssuePriority.medium => 'Medium',
    IssuePriority.low => 'Low',
  };
}
