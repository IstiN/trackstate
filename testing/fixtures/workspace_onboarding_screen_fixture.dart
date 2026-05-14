import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../components/screens/workspace_onboarding_screen.dart';
import '../core/interfaces/workspace_onboarding_screen.dart';
import '../frameworks/flutter/flutter_workspace_onboarding_driver.dart';

Future<WorkspaceOnboardingScreenHandle> launchWorkspaceOnboardingFixture(
  WidgetTester tester, {
  TrackStateRepository? repository,
  TrackStateRepository Function()? repositoryFactory,
  required WorkspaceProfileService workspaceProfileService,
  HostedRepositoryLoader? openHostedRepository,
  LocalRepositoryLoader? openLocalRepository,
  Map<String, Object>? sharedPreferences,
}) async {
  final driver = FlutterWorkspaceOnboardingDriver(tester);
  await driver.launchApp(
    repository: repository,
    repositoryFactory: repositoryFactory,
    workspaceProfileService: workspaceProfileService,
    openHostedRepository: openHostedRepository,
    openLocalRepository: openLocalRepository,
    sharedPreferences: sharedPreferences,
  );
  return WorkspaceOnboardingScreen(driver: driver, onDispose: driver.resetView);
}
