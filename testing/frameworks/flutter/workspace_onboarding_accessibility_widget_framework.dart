import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/workspace_onboarding_accessibility_robot.dart';
import '../../core/interfaces/workspace_onboarding_accessibility_screen.dart';

class WorkspaceOnboardingAccessibilityWidgetFramework {
  WorkspaceOnboardingAccessibilityWidgetFramework(
    this.tester, {
    required this.repository,
    this.sharedPreferences = const <String, Object>{},
  });

  final WidgetTester tester;
  final TrackStateRepository repository;
  final Map<String, Object> sharedPreferences;

  Future<WorkspaceOnboardingAccessibilityScreenHandle> launch() async {
    SharedPreferences.setMockInitialValues(sharedPreferences);
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    await tester.pumpWidget(
      TrackStateApp(
        key: const ValueKey('ts-705-app'),
        repositoryFactory: () => repository,
      ),
    );
    await tester.pumpAndSettle();
    return WorkspaceOnboardingAccessibilityRobot(tester);
  }

  void dispose() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }
}

Future<WorkspaceOnboardingAccessibilityScreenHandle>
launchWorkspaceOnboardingAccessibilityWidgetScreen(
  WidgetTester tester, {
  TrackStateRepository repository = const DemoTrackStateRepository(),
  Map<String, Object> sharedPreferences = const <String, Object>{},
}) async {
  final framework = WorkspaceOnboardingAccessibilityWidgetFramework(
    tester,
    repository: repository,
    sharedPreferences: sharedPreferences,
  );
  addTearDown(framework.dispose);
  return framework.launch();
}
