import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/jql_search_accessibility_robot.dart';
import '../../core/interfaces/jql_search_accessibility_screen.dart';
import '../../fixtures/repositories/jql_search_pagination_repository.dart';

class JqlSearchAccessibilityWidgetFramework {
  JqlSearchAccessibilityWidgetFramework(
    this.tester, {
    required this.repository,
    this.sharedPreferences = const <String, Object>{},
  });

  final WidgetTester tester;
  final TrackStateRepository repository;
  final Map<String, Object> sharedPreferences;

  Future<JqlSearchAccessibilityScreenHandle> launch() async {
    SharedPreferences.setMockInitialValues(sharedPreferences);
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    await tester.pumpWidget(
      TrackStateApp(key: const ValueKey('ts-318-app'), repository: repository),
    );
    await tester.pumpAndSettle();
    return JqlSearchAccessibilityRobot(tester);
  }

  void dispose() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }
}

Future<JqlSearchAccessibilityScreenHandle>
launchJqlSearchAccessibilityWidgetScreen(
  WidgetTester tester, {
  TrackStateRepository? repository,
  Map<String, Object> sharedPreferences = const <String, Object>{},
}) async {
  final framework = JqlSearchAccessibilityWidgetFramework(
    tester,
    repository: repository ?? buildJqlSearchPaginationRepository(),
    sharedPreferences: sharedPreferences,
  );
  addTearDown(framework.dispose);
  return framework.launch();
}
