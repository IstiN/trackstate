import '../models/workspace_shell_entry_point_observation.dart';
import '../models/workspace_onboarding_state.dart';

abstract interface class WorkspaceOnboardingScreenHandle {
  Future<void> openAddWorkspace();

  Future<void> chooseExistingFolder();

  Future<void> chooseHostedRepository();

  Future<void> chooseHostedRepositorySuggestion(String fullName);

  Future<void> enterHostedRepository(String repository);

  Future<void> enterHostedBranch(String branch);

  Future<void> submit();

  WorkspaceOnboardingState captureState();

  WorkspaceShellEntryPointObservation observeShellEntryPoint({
    required String workspaceDisplayName,
  });

  bool isAccessCalloutVisible({required String title, required String message});

  bool isAccessCalloutActionVisible({
    required String title,
    required String message,
    required String actionLabel,
  });

  void dispose();
}
