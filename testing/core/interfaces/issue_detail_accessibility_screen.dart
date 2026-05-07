import '../models/status_badge_contrast_observation.dart';

abstract interface class IssueDetailAccessibilityScreenHandle {
  Future<void> openSearch();

  Future<void> selectIssue(String issueKey, String issueSummary);

  bool showsIssueDetail(String issueKey);

  List<String> visibleTextsWithinIssueDetail(String issueKey);

  List<String> semanticsLabelsInIssueDetail(String issueKey);

  List<String> semanticsLabelsInIssueDetailTraversal(String issueKey);

  List<String> commentActionLabels(String issueKey);

  StatusBadgeContrastObservation observeStatusBadgeContrast(
    String issueKey,
    String label,
  );
}
