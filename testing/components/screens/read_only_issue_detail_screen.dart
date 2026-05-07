import '../../core/interfaces/read_only_issue_detail_screen.dart';
import '../../core/models/action_availability.dart';
import '../pages/issue_detail_page.dart';

class ReadOnlyIssueDetailScreen implements ReadOnlyIssueDetailScreenHandle {
  const ReadOnlyIssueDetailScreen({
    required this.page,
    required void Function() onDispose,
  }) : _onDispose = onDispose;

  final IssueDetailPage page;
  final void Function() _onDispose;

  @override
  Future<void> openSearch() => page.openSearch();

  @override
  Future<void> selectIssue(String issueKey, String issueSummary) =>
      page.selectIssue(issueKey, issueSummary);

  @override
  bool showsIssueDetail(String issueKey) => page.showsIssueDetail(issueKey);

  @override
  bool showsIssueKey(String issueKey) => page.showsIssueKey(issueKey);

  @override
  bool showsSummary(String issueKey, String summary) =>
      page.showsSummary(issueKey, summary);

  @override
  bool showsAcceptanceCriterion(String issueKey, String criterion) =>
      page.showsAcceptanceCriterion(issueKey, criterion);

  @override
  ActionAvailability transitionAction(String issueKey) =>
      page.transitionAction(issueKey);

  @override
  ActionAvailability editAction(String issueKey) => page.editAction(issueKey);

  @override
  ActionAvailability commentAction(String issueKey) =>
      page.commentAction(issueKey);

  @override
  bool hasReadOnlyExplanation(String issueKey) =>
      page.hasReadOnlyExplanation(issueKey);

  @override
  String describeObservedState(String issueKey) =>
      page.describeObservedState(issueKey);

  @override
  void dispose() {
    _onDispose();
  }
}
