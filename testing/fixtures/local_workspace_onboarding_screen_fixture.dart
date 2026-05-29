import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/services/workspace_directory_picker.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../components/screens/local_workspace_onboarding_screen.dart';
import '../core/interfaces/local_workspace_onboarding_screen.dart';
import '../frameworks/flutter/flutter_local_workspace_onboarding_driver.dart';

Future<LocalWorkspaceOnboardingScreenHandle>
launchLocalWorkspaceOnboardingFixture(
  WidgetTester tester, {
  required WorkspaceProfileService workspaceProfileService,
  required LocalWorkspaceOnboardingService onboardingService,
  required WorkspaceDirectoryPicker directoryPicker,
  LocalRepositoryLoader? openLocalRepository,
  Map<String, Object>? sharedPreferences,
}) async {
  final driver = FlutterLocalWorkspaceOnboardingDriver(tester);
  await driver.launchApp(
    workspaceProfileService: workspaceProfileService,
    onboardingService: onboardingService,
    directoryPicker: directoryPicker,
    openLocalRepository: openLocalRepository,
    sharedPreferences: sharedPreferences,
  );
  return LocalWorkspaceOnboardingScreen(
    driver: driver,
    onDispose: driver.resetView,
  );
}
