import 'local_workspace_onboarding_service.dart';

LocalWorkspaceOnboardingService createLocalWorkspaceOnboardingService() =>
    const UnsupportedLocalWorkspaceOnboardingService();

class UnsupportedLocalWorkspaceOnboardingService
    implements LocalWorkspaceOnboardingService {
  const UnsupportedLocalWorkspaceOnboardingService();

  @override
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath) async =>
      throw const LocalWorkspaceOnboardingException(
        'Local workspace onboarding is not available in this build.',
      );

  @override
  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  }) async => throw const LocalWorkspaceOnboardingException(
    'Local workspace onboarding is not available in this build.',
  );
}
