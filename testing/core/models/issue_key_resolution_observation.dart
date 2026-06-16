class IssueKeyResolutionObservation {
  const IssueKeyResolutionObservation({
    required this.key,
    required this.summary,
    required this.indexPath,
    required this.storagePath,
    required this.parentKey,
    required this.parentPath,
    required this.searchResultKeys,
    required this.acceptanceCriteria,
  });

  final String key;
  final String summary;
  final String? indexPath;
  final String storagePath;
  final String? parentKey;
  final String? parentPath;
  final List<String> searchResultKeys;
  final List<String> acceptanceCriteria;
}
