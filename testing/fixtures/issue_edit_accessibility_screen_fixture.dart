import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../components/factories/testing_dependencies.dart';
import '../components/screens/issue_edit_accessibility_robot.dart';
import '../components/screens/issue_edit_accessibility_screen.dart';
import '../core/interfaces/issue_edit_accessibility_screen.dart';

Future<IssueEditAccessibilityScreenHandle> launchIssueEditAccessibilityFixture(
  WidgetTester tester,
) async {
  SharedPreferences.setMockInitialValues({});

  final screen = IssueEditAccessibilityScreen(
    tester: tester,
    app: defaultTestingDependencies.createTrackStateAppScreen(tester),
    robot: IssueEditAccessibilityRobot(tester),
  );
  await screen.launch();
  return screen;
}
