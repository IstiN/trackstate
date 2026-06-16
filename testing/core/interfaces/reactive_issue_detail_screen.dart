import 'read_only_issue_detail_screen.dart';

abstract interface class ReactiveIssueDetailScreenHandle
    implements ReadOnlyIssueDetailScreenHandle {
  Future<void> synchronizeSessionToReadOnly();
}
