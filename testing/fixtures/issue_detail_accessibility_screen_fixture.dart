import 'package:flutter_test/flutter_test.dart';

import '../components/screens/issue_detail_accessibility_robot.dart';
import '../frameworks/flutter/issue_detail_accessibility_widget_framework.dart';

Future<IssueDetailAccessibilityRobot> launchIssueDetailAccessibilityFixture(
  WidgetTester tester,
) {
  return launchIssueDetailAccessibilityWidgetScreen(tester);
}
