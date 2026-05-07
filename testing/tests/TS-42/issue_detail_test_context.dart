import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/read_only_issue_detail_screen.dart';
import '../../frameworks/flutter/read_only_issue_detail_widget_framework.dart';

Future<ReadOnlyIssueDetailScreen> launchReadOnlyIssueDetailScreen(
  WidgetTester tester,
) {
  return ReadOnlyIssueDetailWidgetFramework(tester).launch();
}
