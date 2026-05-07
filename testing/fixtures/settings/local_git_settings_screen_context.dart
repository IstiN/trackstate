import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../frameworks/flutter/flutter_local_git_repository_factory.dart';

SettingsScreenRobot createLocalGitSettingsScreenRobot(WidgetTester tester) {
  return SettingsScreenRobot(
    tester,
    localGitRepositoryFactory: FlutterLocalGitRepositoryFactory(tester),
  );
}
