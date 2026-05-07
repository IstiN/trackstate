import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/read_only_issue_detail_screen_component.dart';
import '../../components/screens/read_only_issue_detail_screen.dart';

Future<ReadOnlyIssueDetailScreen> launchReadOnlyIssueDetailScreen(
  WidgetTester tester,
) {
  return createReadOnlyIssueDetailScreen(tester);
}
