import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../components/factories/testing_dependencies.dart';
import '../components/screens/loading_state_visual_quality_robot.dart';
import '../components/screens/loading_state_visual_quality_screen.dart';
import '../core/interfaces/loading_state_visual_quality_screen.dart';
import 'repositories/ts453_bootstrap_loading_repository.dart';

Future<LoadingStateVisualQualityScreenHandle>
launchLoadingStateVisualQualityFixture(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({});

  final screen = LoadingStateVisualQualityScreen(
    app: defaultTestingDependencies.createTrackStateAppScreen(tester),
    robot: LoadingStateVisualQualityRobot(tester),
    repository: const Ts453BootstrapLoadingRepository(),
  );
  await screen.launch();
  return screen;
}
