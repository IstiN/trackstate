import '../../core/interfaces/read_only_issue_detail_harness.dart';
import '../../core/interfaces/read_only_issue_detail_screen.dart';
import '../../core/interfaces/test_driver.dart';
import '../pages/issue_detail_page.dart';
import 'read_only_issue_detail_screen.dart';

Future<ReadOnlyIssueDetailScreenHandle> createReadOnlyIssueDetailScreen({
  required TestDriver driver,
  required ReadOnlyIssueDetailHarness harness,
}) async {
  await harness.launch();
  return ReadOnlyIssueDetailScreen(
    page: IssueDetailPage(driver),
    onDispose: harness.dispose,
  );
}
