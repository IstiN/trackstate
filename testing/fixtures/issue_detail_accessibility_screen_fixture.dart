import 'package:flutter_test/flutter_test.dart';

import '../core/interfaces/issue_detail_accessibility_screen.dart';
import '../frameworks/flutter/issue_detail_accessibility_widget_framework.dart';

Future<IssueDetailAccessibilityScreenHandle>
launchIssueDetailAccessibilityFixture(WidgetTester tester) {
  return launchIssueDetailAccessibilityWidgetScreen(tester);
}
