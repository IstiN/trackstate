import '../models/issue_detail_icon_observation.dart';
import '../models/issue_detail_row_style_observation.dart';
import '../models/issue_detail_text_contrast_observation.dart';
import '../models/status_badge_contrast_observation.dart';

abstract interface class IssueDetailAccessibilityScreenHandle {
  Future<void> openSearch();

  Future<void> selectIssue(String issueKey, String issueSummary);

  Future<void> selectCollaborationTab(String issueKey, String label);

  bool showsIssueDetail(String issueKey);

  List<String> visibleTextsWithinIssueDetail(String issueKey);

  List<String> semanticsLabelsInIssueDetail(String issueKey);

  List<String> semanticsLabelsInIssueDetailTraversal(String issueKey);

  List<String> buttonLabelsInIssueDetail(String issueKey);

  List<String> commentActionLabels(String issueKey);

  StatusBadgeContrastObservation observeStatusBadgeContrast(
    String issueKey,
    String label,
  );

  IssueDetailTextContrastObservation observeDecoratedRowTextContrast(
    String issueKey, {
    required String rowAnchorText,
    required String text,
  });

  IssueDetailRowStyleObservation observeDecoratedRowStyle(
    String issueKey, {
    required String rowAnchorText,
  });

  IssueDetailIconObservation observeDecoratedRowIcon(
    String issueKey, {
    required String rowAnchorText,
    required String semanticLabel,
  });
}
