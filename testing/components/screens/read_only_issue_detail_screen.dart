import '../pages/issue_detail_page.dart';

class ReadOnlyIssueDetailScreen {
  const ReadOnlyIssueDetailScreen({
    required this.page,
    required void Function() onDispose,
  }) : _onDispose = onDispose;

  final IssueDetailPage page;
  final void Function() _onDispose;

  void dispose() {
    _onDispose();
  }
}
