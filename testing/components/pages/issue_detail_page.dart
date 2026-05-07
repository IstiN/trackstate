import '../../core/interfaces/test_driver.dart';
import '../../core/models/action_availability.dart';

class IssueDetailPage {
  const IssueDetailPage(this.driver);

  final TestDriver driver;

  Future<void> openSearch() => driver.tapSemanticsLabel(RegExp('JQL Search'));

  Future<void> openIssue(String issueKey, String issueSummary) async {
    await openSearch();
    await selectIssue(issueKey, issueSummary);
  }

  Future<void> selectIssue(String issueKey, String issueSummary) =>
      driver.tapText(issueSummary);

  Pattern openIssueLink(String issueKey, String issueSummary) => RegExp(
    '^Open ${RegExp.escape(issueKey)} ${RegExp.escape(issueSummary)}\$',
  );

  Pattern issueDetailLabel(String issueKey) =>
      RegExp('^Issue detail ${RegExp.escape(issueKey)}\$');

  bool showsIssueDetail(String issueKey) =>
      driver.hasSemanticsLabel(issueDetailLabel(issueKey));

  bool showsIssueLink(String issueKey, String issueSummary) =>
      driver.hasSemanticsLabel(openIssueLink(issueKey, issueSummary));

  bool showsIssueKey(String issueKey) => driver.hasText(issueKey);

  bool showsSummary(String summary) => driver.hasText(summary);

  bool showsAcceptanceCriterion(String criterion) => driver.hasText(criterion);

  ActionAvailability get transitionAction =>
      driver.getActionAvailability('Transition');

  ActionAvailability get editAction => driver.getActionAvailability('Edit');

  ActionAvailability get commentAction =>
      driver.getActionAvailability('Comments');

  bool get hasReadOnlyExplanation => driver.hasAnyMessage([
    RegExp('permission required', caseSensitive: false),
    RegExp('write access', caseSensitive: false),
    RegExp('write permission', caseSensitive: false),
    RegExp('read[- ]only (repository|session|access)', caseSensitive: false),
  ]);

  String describeObservedState() => [
    transitionAction.describe(),
    editAction.describe(),
    commentAction.describe(),
    'readOnlyExplanationVisible=$hasReadOnlyExplanation',
  ].join(', ');
}
