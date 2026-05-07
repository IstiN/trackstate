import 'package:flutter_test/flutter_test.dart';

import '../../frameworks/flutter/read_only_issue_detail_widget_framework.dart';
import 'read_only_issue_detail_screen.dart';

Future<ReadOnlyIssueDetailScreen> createReadOnlyIssueDetailScreen(
  WidgetTester tester,
) {
  return ReadOnlyIssueDetailWidgetFramework(tester).launch();
}
