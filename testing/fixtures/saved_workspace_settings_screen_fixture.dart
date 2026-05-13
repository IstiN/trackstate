import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../components/screens/saved_workspace_settings_screen.dart';
import '../core/interfaces/saved_workspace_settings_screen.dart';
import '../frameworks/flutter/flutter_saved_workspace_settings_driver.dart';

Future<SavedWorkspaceSettingsScreenHandle> launchSavedWorkspaceSettingsFixture(
  WidgetTester tester, {
  TrackStateRepository repository = const DemoTrackStateRepository(),
  required WorkspaceProfileService workspaceProfileService,
  HostedRepositoryLoader? openHostedRepository,
  LocalRepositoryLoader? openLocalRepository,
  Map<String, Object> sharedPreferences = const <String, Object>{},
}) async {
  final driver = FlutterSavedWorkspaceSettingsDriver(tester);
  await driver.launchApp(
    repository: repository,
    workspaceProfileService: workspaceProfileService,
    openHostedRepository: openHostedRepository,
    openLocalRepository: openLocalRepository,
    sharedPreferences: sharedPreferences,
  );
  return SavedWorkspaceSettingsScreen(
    driver: driver,
    onDispose: driver.resetView,
  );
}
