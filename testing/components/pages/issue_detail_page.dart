import '../../core/models/action_availability.dart';
import '../../frameworks/flutter/widget_test_driver.dart';

class IssueDetailPage {
  const IssueDetailPage(this.driver);

  final WidgetTestDriver driver;

  Future<void> openIssue(String issueKey, String issueSummary) async {
    await driver.tapText('JQL Search');
  }

  bool showsIssueKey(String issueKey) => driver.hasText(issueKey);

  bool showsSummary(String summary) => driver.hasText(summary);

  ActionAvailability get transitionAction => ActionAvailability(
    label: 'Transition',
    visible: driver.hasLabeledControl('Transition'),
    enabled: driver.isFilledButtonEnabled('Transition'),
  );

  ActionAvailability get editAction => _unavailableWhenMissing('Edit');

  ActionAvailability get commentAction => _unavailableWhenMissing('Comment');

  bool get permissionMessageVisible => driver.hasText('Permission required');

  String describeObservedState() => [
    transitionAction.describe(),
    editAction.describe(),
    commentAction.describe(),
    'permissionMessageVisible=$permissionMessageVisible',
  ].join(', ');

  ActionAvailability _unavailableWhenMissing(String label) {
    final visible = driver.hasLabeledControl(label);
    return ActionAvailability(label: label, visible: visible, enabled: visible);
  }
}
