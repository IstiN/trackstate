import '../../core/interfaces/reactive_issue_detail_harness.dart';
import '../../core/interfaces/reactive_issue_detail_screen.dart';
import '../../core/interfaces/test_driver.dart';
import '../pages/issue_detail_page.dart';
import 'reactive_issue_detail_screen.dart';

Future<ReactiveIssueDetailScreenHandle> createReactiveIssueDetailScreen({
  required TestDriver driver,
  required ReactiveIssueDetailHarness harness,
}) async {
  await harness.launch();
  return ReactiveIssueDetailScreen(
    page: IssueDetailPage(driver),
    onSynchronizeSessionToReadOnly: harness.synchronizeSessionToReadOnly,
    onDispose: harness.dispose,
  );
}
