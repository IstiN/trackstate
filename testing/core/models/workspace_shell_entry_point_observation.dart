class WorkspaceShellEntryPointObservation {
  const WorkspaceShellEntryPointObservation({
    required this.isAddWorkspaceVisible,
    required this.isWorkspaceSwitcherVisible,
    required this.addWorkspaceHasSemanticLabel,
    required this.workspaceSwitcherHasSemanticLabel,
    required this.currentWorkspaceIncludedInSwitcherLabel,
    required this.sharedTopBarRow,
    required this.verticalCenterDelta,
    required this.horizontalGap,
    required this.addWorkspaceBeforeSwitcher,
    required this.addWorkspaceRect,
    required this.workspaceSwitcherRect,
  });

  final bool isAddWorkspaceVisible;
  final bool isWorkspaceSwitcherVisible;
  final bool addWorkspaceHasSemanticLabel;
  final bool workspaceSwitcherHasSemanticLabel;
  final bool currentWorkspaceIncludedInSwitcherLabel;
  final bool sharedTopBarRow;
  final double? verticalCenterDelta;
  final double? horizontalGap;
  final bool addWorkspaceBeforeSwitcher;
  final Map<String, double>? addWorkspaceRect;
  final Map<String, double>? workspaceSwitcherRect;

  bool get hasAccessibleShellControls =>
      isAddWorkspaceVisible &&
      isWorkspaceSwitcherVisible &&
      addWorkspaceHasSemanticLabel &&
      workspaceSwitcherHasSemanticLabel &&
      currentWorkspaceIncludedInSwitcherLabel;

  bool get isPositionedBesideWorkspaceSwitcher {
    final verticalCenterDelta = this.verticalCenterDelta;
    final horizontalGap = this.horizontalGap;
    return sharedTopBarRow &&
        verticalCenterDelta != null &&
        horizontalGap != null &&
        verticalCenterDelta <= 4 &&
        horizontalGap >= 0 &&
        horizontalGap <= 24 &&
        addWorkspaceBeforeSwitcher;
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'is_add_workspace_visible': isAddWorkspaceVisible,
    'is_workspace_switcher_visible': isWorkspaceSwitcherVisible,
    'add_workspace_has_semantic_label': addWorkspaceHasSemanticLabel,
    'workspace_switcher_has_semantic_label': workspaceSwitcherHasSemanticLabel,
    'current_workspace_included_in_switcher_label':
        currentWorkspaceIncludedInSwitcherLabel,
    'shared_top_bar_row': sharedTopBarRow,
    'vertical_center_delta': verticalCenterDelta,
    'horizontal_gap': horizontalGap,
    'add_workspace_before_switcher': addWorkspaceBeforeSwitcher,
    'add_workspace_rect': addWorkspaceRect,
    'workspace_switcher_rect': workspaceSwitcherRect,
  };
}
