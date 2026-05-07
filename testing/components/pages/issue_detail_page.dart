import '../../core/interfaces/test_driver.dart';
import '../../core/models/action_availability.dart';

class IssueDetailPage {
  const IssueDetailPage(this.driver);

  final TestDriver driver;

  Future<void> openIssue(String issueKey, String issueSummary) async {
    await driver.tapText('JQL Search');
    final issueLink = RegExp(
      '^Open ${RegExp.escape(issueKey)} ${RegExp.escape(issueSummary)}\$',
    );
    if (driver.hasSemanticsLabel(issueLink)) {
      await driver.tapSemanticsLabel(issueLink);
    }
  }

  bool showsIssueKey(String issueKey) => driver.hasText(issueKey);

  bool showsSummary(String summary) => driver.hasText(summary);

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
