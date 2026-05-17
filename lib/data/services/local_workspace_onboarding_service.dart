import 'local_workspace_onboarding_service_stub.dart'
    if (dart.library.io) 'local_workspace_onboarding_service_io.dart'
    as platform;

enum LocalWorkspaceInspectionState { readyToOpen, readyToInitialize, blocked }

class LocalWorkspaceInspection {
  const LocalWorkspaceInspection({
    required this.folderPath,
    required this.state,
    required this.message,
    required this.suggestedWorkspaceName,
    required this.suggestedWriteBranch,
    this.detectedWriteBranch,
    this.hasGitRepository = false,
    this.needsGitInitialization = false,
  });

  final String folderPath;
  final LocalWorkspaceInspectionState state;
  final String message;
  final String suggestedWorkspaceName;
  final String suggestedWriteBranch;
  final String? detectedWriteBranch;
  final bool hasGitRepository;
  final bool needsGitInitialization;

  bool get canOpen => state == LocalWorkspaceInspectionState.readyToOpen;
  bool get canInitialize =>
      state == LocalWorkspaceInspectionState.readyToInitialize;
}

class LocalWorkspaceSetupResult {
  const LocalWorkspaceSetupResult({
    required this.folderPath,
    required this.displayName,
    required this.defaultBranch,
    required this.writeBranch,
    required this.projectKey,
  });

  final String folderPath;
  final String displayName;
  final String defaultBranch;
  final String writeBranch;
  final String projectKey;
}

class LocalWorkspaceOnboardingException implements Exception {
  const LocalWorkspaceOnboardingException(this.message);

  final String message;

  @override
  String toString() => message;
}

abstract interface class LocalWorkspaceOnboardingService {
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath);

  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  });
}

LocalWorkspaceOnboardingService createLocalWorkspaceOnboardingService() =>
    platform.createLocalWorkspaceOnboardingService();
