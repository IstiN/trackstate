import '../models/local_workspace_onboarding_state.dart';

abstract interface class LocalWorkspaceOnboardingScreenHandle {
  Future<void> chooseInitializeFolder();

  LocalWorkspaceOnboardingState captureState();

  void dispose();
}
