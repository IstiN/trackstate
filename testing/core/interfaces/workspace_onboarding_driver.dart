import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/services/workspace_directory_picker.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../models/workspace_onboarding_state.dart';

abstract interface class WorkspaceOnboardingDriver {
  Future<void> launchApp({
    TrackStateRepository? repository,
    TrackStateRepository Function()? repositoryFactory,
    required WorkspaceProfileService workspaceProfileService,
    HostedRepositoryLoader? openHostedRepository,
    LocalRepositoryLoader? openLocalRepository,
    LocalWorkspaceOnboardingService? localWorkspaceOnboardingService,
    WorkspaceDirectoryPicker? workspaceDirectoryPicker,
    Map<String, Object>? sharedPreferences,
  });

  Future<void> openAddWorkspace();

  Future<void> selectExistingFolder();

  Future<void> selectHostedRepository();

  Future<void> selectHostedRepositorySuggestion(String fullName);

  Future<void> enterHostedRepository(String repository);

  Future<void> enterHostedBranch(String branch);

  Future<void> submit();

  WorkspaceOnboardingState captureState();

  bool isAccessCalloutVisible({required String title, required String message});

  bool isAccessCalloutActionVisible({
    required String title,
    required String message,
    required String actionLabel,
  });

  void resetView();
}
