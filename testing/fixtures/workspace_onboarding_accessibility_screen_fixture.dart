import 'package:flutter_test/flutter_test.dart';

import '../core/interfaces/workspace_onboarding_accessibility_screen.dart';
import '../frameworks/flutter/workspace_onboarding_accessibility_widget_framework.dart';

Future<WorkspaceOnboardingAccessibilityScreenHandle>
launchWorkspaceOnboardingAccessibilityFixture(WidgetTester tester) {
  return launchWorkspaceOnboardingAccessibilityWidgetScreen(tester);
}
