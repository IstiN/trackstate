import '../models/local_workspace_onboarding_state.dart';

abstract interface class LocalWorkspaceOnboardingScreenHandle {
  Future<void> chooseExistingFolder();

  Future<void> chooseInitializeFolder();

  Future<void> enterWorkspaceName(String value);

  Future<void> enterWriteBranch(String value);

  Future<void> submit();
  LocalWorkspaceOnboardingState captureState();

  void dispose();
}
