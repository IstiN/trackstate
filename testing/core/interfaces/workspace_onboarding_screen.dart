import '../models/workspace_onboarding_state.dart';

abstract interface class WorkspaceOnboardingScreenHandle {
  Future<void> openAddWorkspace();

  Future<void> chooseOpenExistingFolder();

  Future<void> chooseHostedRepository();

  Future<void> chooseHostedRepositorySuggestion(String fullName);

  Future<void> enterLocalWorkspaceName(String value);

  Future<void> enterLocalWriteBranch(String value);

  Future<void> submit();

  WorkspaceOnboardingState captureState();

  bool isAccessCalloutVisible({required String title, required String message});

  bool isAccessCalloutActionVisible({
    required String title,
    required String message,
    required String actionLabel,
  });

  void dispose();
}
