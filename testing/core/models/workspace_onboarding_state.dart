class WorkspaceOnboardingState {
  const WorkspaceOnboardingState({
    required this.isOnboardingVisible,
    required this.isDashboardVisible,
    required this.hostedRepositoryValue,
    required this.hostedBranchValue,
    required this.localWorkspaceNameValue,
    required this.localWriteBranchValue,
    required this.primaryActionLabel,
    required this.isPrimaryActionEnabled,
    required this.repositoryAccessTopBarLabel,
    required this.visibleTexts,
    required this.interactiveSemanticsLabels,
  });

  final bool isOnboardingVisible;
  final bool isDashboardVisible;
  final String? hostedRepositoryValue;
  final String? hostedBranchValue;
  final String? localWorkspaceNameValue;
  final String? localWriteBranchValue;
  final String primaryActionLabel;
  final bool isPrimaryActionEnabled;
  final String? repositoryAccessTopBarLabel;
  final List<String> visibleTexts;
  final List<String> interactiveSemanticsLabels;
}
