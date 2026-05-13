class SavedWorkspaceSettingsState {
  const SavedWorkspaceSettingsState({
    required this.isSavedWorkspacesVisible,
    required this.workspaceLabels,
    required this.selectedWorkspaceLabels,
    required this.activeLabelCount,
    required this.dialogTexts,
    required this.visibleTexts,
  });

  final bool isSavedWorkspacesVisible;
  final List<String> workspaceLabels;
  final List<String> selectedWorkspaceLabels;
  final int activeLabelCount;
  final List<String> dialogTexts;
  final List<String> visibleTexts;
}
