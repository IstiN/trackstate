import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/services/workspace_directory_picker.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../models/local_workspace_onboarding_state.dart';

abstract interface class LocalWorkspaceOnboardingDriver {
  Future<void> launchApp({
    required WorkspaceProfileService workspaceProfileService,
    required LocalWorkspaceOnboardingService onboardingService,
    required WorkspaceDirectoryPicker directoryPicker,
    LocalRepositoryLoader? openLocalRepository,
    Map<String, Object>? sharedPreferences,
  });

  Future<void> chooseExistingFolder();

  Future<void> chooseInitializeFolder();

  Future<void> enterWorkspaceName(String value);

  Future<void> enterWriteBranch(String value);

  LocalWorkspaceOnboardingState captureState();

  void resetView();
}
