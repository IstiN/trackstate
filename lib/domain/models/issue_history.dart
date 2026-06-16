enum IssueHistoryChangeType {
  created,
  updated,
  deleted,
  restored,
  archived,
  moved,
  added,
  removed,
}

enum IssueHistoryEntity { issue, comment, attachment, hierarchy }

class IssueHistoryEntry {
  const IssueHistoryEntry({
    required this.commitSha,
    required this.timestamp,
    required this.author,
    required this.changeType,
    required this.affectedEntity,
    required this.summary,
    required this.changedPaths,
    this.affectedEntityId,
    this.fieldName,
    this.before,
    this.after,
  });

  final String commitSha;
  final String timestamp;
  final String author;
  final IssueHistoryChangeType changeType;
  final IssueHistoryEntity affectedEntity;
  final String summary;
  final List<String> changedPaths;
  final String? affectedEntityId;
  final String? fieldName;
  final String? before;
  final String? after;
}
