import '../models/action_availability.dart';

abstract interface class ReadOnlyIssueDetailScreenHandle {
  Future<void> openSearch();

  Future<void> selectIssue(String issueKey, String issueSummary);

  bool showsIssueDetail(String issueKey);

  bool showsIssueKey(String issueKey);

  bool showsSummary(String issueKey, String summary);

  bool showsAcceptanceCriterion(String issueKey, String criterion);

  ActionAvailability transitionAction(String issueKey);

  ActionAvailability editAction(String issueKey);

  ActionAvailability commentAction(String issueKey);

  bool hasReadOnlyExplanation(String issueKey);

  String describeObservedState(String issueKey);

  void dispose();
}
