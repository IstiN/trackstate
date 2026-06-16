import 'core_enums.dart';

extension IssueTypeLabel on IssueType {
  String get id => switch (this) {
    IssueType.epic => 'epic',
    IssueType.story => 'story',
    IssueType.task => 'task',
    IssueType.subtask => 'subtask',
    IssueType.bug => 'bug',
  };

  String get label => switch (this) {
    IssueType.epic => 'Epic',
    IssueType.story => 'Story',
    IssueType.task => 'Task',
    IssueType.subtask => 'Sub-task',
    IssueType.bug => 'Bug',
  };
}

extension IssueStatusLabel on IssueStatus {
  String get id => switch (this) {
    IssueStatus.todo => 'todo',
    IssueStatus.inProgress => 'in-progress',
    IssueStatus.inReview => 'in-review',
    IssueStatus.done => 'done',
  };

  String get label => switch (this) {
    IssueStatus.todo => 'To Do',
    IssueStatus.inProgress => 'In Progress',
    IssueStatus.inReview => 'In Review',
    IssueStatus.done => 'Done',
  };
}

extension IssuePriorityLabel on IssuePriority {
  String get id => switch (this) {
    IssuePriority.highest => 'highest',
    IssuePriority.high => 'high',
    IssuePriority.medium => 'medium',
    IssuePriority.low => 'low',
  };

  String get label => switch (this) {
    IssuePriority.highest => 'Highest',
    IssuePriority.high => 'High',
    IssuePriority.medium => 'Medium',
    IssuePriority.low => 'Low',
  };
}
