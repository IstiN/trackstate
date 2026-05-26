class LocalWorkspaceOnboardingState {
  const LocalWorkspaceOnboardingState({
    required this.isOnboardingVisible,
    required this.isInitializeActionVisible,
    required this.statusLabel,
    required this.inspectionMessage,
    required this.folderPath,
    required this.workspaceNameValue,
    required this.writeBranchValue,
    required this.submitLabel,
    required this.isSubmitVisible,
    required this.isSubmitEnabled,
    required this.visibleTexts,
  });

  final bool isOnboardingVisible;
  final bool isInitializeActionVisible;
  final String? statusLabel;
  final String? inspectionMessage;
  final String? folderPath;
  final String? workspaceNameValue;
  final String? writeBranchValue;
  final String? submitLabel;
  final bool isSubmitVisible;
  final bool isSubmitEnabled;
  final List<String> visibleTexts;
}
