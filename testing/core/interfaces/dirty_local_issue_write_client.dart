class DirtyLocalIssueFileSnapshot {
  const DirtyLocalIssueFileSnapshot({
    required this.content,
    required this.revision,
  });

  final String content;
  final String? revision;
}

class DirtyLocalIssueWriteRequest {
  const DirtyLocalIssueWriteRequest({
    required this.path,
    required this.content,
    required this.message,
    required this.branch,
    required this.expectedRevision,
  });

  final String path;
  final String content;
  final String message;
  final String branch;
  final String? expectedRevision;
}

abstract interface class DirtyLocalIssueWriteClient {
  Future<String> resolveWriteBranch();

  Future<DirtyLocalIssueFileSnapshot> readTextFile(
    String path, {
    required String ref,
  });

  Future<void> writeTextFile(DirtyLocalIssueWriteRequest request);
}
