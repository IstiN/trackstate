import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../models/saved_workspace_settings_state.dart';

abstract interface class SavedWorkspaceSettingsDriver {
  Future<void> launchApp({
    required TrackStateRepository repository,
    required WorkspaceProfileService workspaceProfileService,
    HostedRepositoryLoader? openHostedRepository,
    LocalRepositoryLoader? openLocalRepository,
    Map<String, Object> sharedPreferences = const <String, Object>{},
  });

  Future<void> openSettings();

  Future<void> tapWorkspaceDelete(String displayName);

  Future<void> tapDialogAction(String label);

  SavedWorkspaceSettingsState captureState();

  void resetView();
}
