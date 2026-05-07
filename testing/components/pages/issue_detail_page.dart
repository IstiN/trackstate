import '../../core/interfaces/test_driver.dart';
import '../../core/models/action_availability.dart';

class IssueDetailPage {
  const IssueDetailPage(this.driver);

  final TestDriver driver;

  static final RegExp _searchPanelLabel = RegExp('^JQL Search\$');

  Future<void> openSearch() => driver.tapText('JQL Search');

  Future<void> openIssue(String issueKey, String issueSummary) async {
    await openSearch();
    await selectIssue(issueKey, issueSummary);
  }

  Future<void> selectIssue(String issueKey, String issueSummary) =>
      driver.tapSemanticsLabel(
        openIssueLink(issueKey, issueSummary),
        within: _searchPanelLabel,
      );

  Pattern openIssueLink(String issueKey, String issueSummary) => RegExp(
    '^Open ${RegExp.escape(issueKey)} ${RegExp.escape(issueSummary)}\$',
  );

  Pattern issueDetailLabel(String issueKey) =>
      RegExp('^Issue detail ${RegExp.escape(issueKey)}\$');

  bool showsIssueDetail(String issueKey) =>
      driver.hasSemanticsLabel(issueDetailLabel(issueKey));

  bool showsIssueLink(String issueKey, String issueSummary) =>
      driver.hasSemanticsLabel(
        openIssueLink(issueKey, issueSummary),
        within: _searchPanelLabel,
      );

  bool showsIssueKey(String issueKey) =>
      driver.hasText(issueKey, within: issueDetailLabel(issueKey));

  bool showsSummary(String issueKey, String summary) =>
      driver.hasText(summary, within: issueDetailLabel(issueKey));

  bool showsAcceptanceCriterion(String issueKey, String criterion) =>
      driver.hasText(criterion, within: issueDetailLabel(issueKey));

  ActionAvailability transitionAction(String issueKey) => driver
      .getActionAvailability('Transition', within: issueDetailLabel(issueKey));

  ActionAvailability editAction(String issueKey) =>
      driver.getActionAvailability('Edit', within: issueDetailLabel(issueKey));

  ActionAvailability commentAction(String issueKey) => driver
      .getActionAvailability('Comments', within: issueDetailLabel(issueKey));

  bool hasReadOnlyExplanation(String issueKey) => driver.hasAnyMessage([
    RegExp('permission required', caseSensitive: false),
    RegExp('write access', caseSensitive: false),
    RegExp('write permission', caseSensitive: false),
    RegExp('read[- ]only (repository|session|access)', caseSensitive: false),
  ], within: issueDetailLabel(issueKey));

  String describeObservedState(String issueKey) => [
    transitionAction(issueKey).describe(),
    editAction(issueKey).describe(),
    commentAction(issueKey).describe(),
    'readOnlyExplanationVisible=${hasReadOnlyExplanation(issueKey)}',
  ].join(', ');
}
