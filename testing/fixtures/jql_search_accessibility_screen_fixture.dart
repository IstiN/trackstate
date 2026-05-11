import 'package:flutter_test/flutter_test.dart';

import '../core/interfaces/jql_search_accessibility_screen.dart';
import '../frameworks/flutter/jql_search_accessibility_widget_framework.dart';

Future<JqlSearchAccessibilityScreenHandle> launchJqlSearchAccessibilityFixture(
  WidgetTester tester,
) {
  return launchJqlSearchAccessibilityWidgetScreen(tester);
}
