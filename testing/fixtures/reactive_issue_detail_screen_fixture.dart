import 'package:flutter_test/flutter_test.dart';

import '../core/interfaces/reactive_issue_detail_screen.dart';
import '../frameworks/flutter/reactive_issue_detail_widget_framework.dart';

Future<ReactiveIssueDetailScreenHandle> launchReactiveIssueDetailFixture(
  WidgetTester tester,
) {
  return launchReactiveIssueDetailWidgetScreen(tester);
}
