import 'package:flutter_test/flutter_test.dart';

import '../core/interfaces/read_only_issue_detail_screen.dart';
import '../frameworks/flutter/read_only_issue_detail_widget_framework.dart';

Future<ReadOnlyIssueDetailScreenHandle> launchReadOnlyIssueDetailFixture(
  WidgetTester tester,
) {
  return launchReadOnlyIssueDetailWidgetScreen(tester);
}

Future<ReadOnlyIssueDetailScreenHandle> launchWritableIssueDetailFixture(
  WidgetTester tester,
) {
  return launchWritableIssueDetailWidgetScreen(tester);
}
