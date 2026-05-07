class ProviderOptionState {
  const ProviderOptionState({
    required this.label,
    required this.visibleCount,
    required this.isSelected,
    this.top,
    this.bottom,
    this.left,
  });

  final String label;
  final int visibleCount;
  final bool isSelected;
  final double? top;
  final double? bottom;
  final double? left;

  bool get isVisible => visibleCount > 0;
}

class SettingsProviderState {
  const SettingsProviderState({
    required this.isProjectSettingsVisible,
    required this.connectGitHubOption,
    required this.localGitOption,
    required this.isFineGrainedTokenVisible,
    required this.isRepositoryPathVisible,
    required this.isWriteBranchVisible,
    this.repositoryPathTop,
    this.repositoryPathBottom,
    this.repositoryPathLeft,
    this.writeBranchTop,
    this.writeBranchBottom,
    this.writeBranchLeft,
  });

  final bool isProjectSettingsVisible;
  final ProviderOptionState connectGitHubOption;
  final ProviderOptionState localGitOption;
  final bool isFineGrainedTokenVisible;
  final bool isRepositoryPathVisible;
  final bool isWriteBranchVisible;
  final double? repositoryPathTop;
  final double? repositoryPathBottom;
  final double? repositoryPathLeft;
  final double? writeBranchTop;
  final double? writeBranchBottom;
  final double? writeBranchLeft;
}
