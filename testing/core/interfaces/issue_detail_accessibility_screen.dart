import '../models/issue_detail_icon_observation.dart';
import '../models/issue_detail_row_style_observation.dart';
import '../models/issue_detail_theme_tokens.dart';
import '../models/issue_detail_text_contrast_observation.dart';
import '../models/status_badge_contrast_observation.dart';

abstract interface class IssueDetailAccessibilityScreenHandle {
  Future<void> openSearch();

  Future<void> selectIssue(String issueKey, String issueSummary);

  Future<void> selectCollaborationTab(String issueKey, String label);

  Future<void> enterCommentComposerText(String issueKey, String text);

  Future<List<String>> collectForwardCollaborationTabFocusOrder(
    String issueKey,
  );

  bool showsIssueDetail(String issueKey);

  List<String> visibleTextsWithinIssueDetail(String issueKey);

  List<String> semanticsLabelsInIssueDetail(String issueKey);

  List<String> semanticsLabelsInIssueDetailTraversal(String issueKey);

  List<String> buttonLabelsInIssueDetail(String issueKey);

  List<String> commentActionLabels(String issueKey);

  bool showsAttachmentsRestrictionCallout(
    String issueKey, {
    required String title,
    required String message,
  });

  bool attachmentsRestrictionCalloutShowsText(
    String issueKey, {
    required String title,
    required String message,
    required String text,
  });

  bool attachmentsRestrictionCalloutIsInline(
    String issueKey, {
    required String tabLabel,
    required String title,
    required String message,
  });

  bool showsAttachmentRow(String issueKey, String attachmentName);

  bool attachmentRowIsBelowAttachmentsRestrictionCallout(
    String issueKey, {
    required String title,
    required String message,
    required String attachmentName,
  });

  bool showsAttachmentsRestrictionAction(
    String issueKey, {
    required String title,
    required String message,
    required String actionLabel,
  });

  Future<void> tapAttachmentsRestrictionAction(
    String issueKey, {
    required String title,
    required String message,
    required String actionLabel,
  });

  String? commentComposerPlaceholderText(String issueKey);

  String? readCommentComposerText(String issueKey);

  IssueDetailThemeTokens themeTokens(String issueKey);

  StatusBadgeContrastObservation observeStatusBadgeContrast(
    String issueKey,
    String label,
  );

  IssueDetailTextContrastObservation observeDecoratedRowTextContrast(
    String issueKey, {
    required String rowAnchorText,
    required String text,
  });

  IssueDetailTextContrastObservation observeCommentComposerEnteredTextContrast(
    String issueKey, {
    required String text,
  });

  IssueDetailTextContrastObservation observeCommentComposerPlaceholderContrast(
    String issueKey,
  );

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
