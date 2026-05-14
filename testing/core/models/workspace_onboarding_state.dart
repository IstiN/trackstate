class WorkspaceOnboardingState {
  const WorkspaceOnboardingState({
    required this.isOnboardingVisible,
    required this.isDashboardVisible,
    required this.hostedRepositoryValue,
    required this.hostedBranchValue,
    required this.localWorkspaceNameValue,
    required this.localWriteBranchValue,
    required this.localFolderPath,
    required this.primaryActionLabel,
    required this.repositoryAccessTopBarLabel,
    required this.visibleTexts,
  });

  final bool isOnboardingVisible;
  final bool isDashboardVisible;
  final String? hostedRepositoryValue;
  final String? hostedBranchValue;
  final String? localWorkspaceNameValue;
  final String? localWriteBranchValue;
  final String? localFolderPath;
  final String? primaryActionLabel;
  final String? repositoryAccessTopBarLabel;
  final List<String> visibleTexts;
}
