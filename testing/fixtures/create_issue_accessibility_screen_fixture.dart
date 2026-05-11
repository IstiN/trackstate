import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../components/factories/testing_dependencies.dart';
import '../components/screens/create_issue_accessibility_robot.dart';
import '../components/screens/create_issue_accessibility_screen.dart';
import '../core/interfaces/create_issue_accessibility_screen.dart';

Future<CreateIssueAccessibilityScreenHandle>
launchCreateIssueAccessibilityFixture(
  WidgetTester tester, {
  double? initialViewportWidth,
  double? initialViewportHeight,
}) async {
  SharedPreferences.setMockInitialValues({});

  final screen = CreateIssueAccessibilityScreen(
    tester: tester,
    app: defaultTestingDependencies.createTrackStateAppScreen(tester),
    robot: CreateIssueAccessibilityRobot(tester),
  );
  await screen.launch(
    initialViewportWidth: initialViewportWidth,
    initialViewportHeight: initialViewportHeight,
  );
  return screen;
}
