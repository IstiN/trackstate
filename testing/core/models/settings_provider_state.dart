enum SettingsProviderOption { hosted, localGit }

class ProviderOptionState {
  const ProviderOptionState({
    required this.option,
    required this.label,
    required this.visibleCount,
    required this.isSelected,
    this.top,
    this.bottom,
    this.left,
  });

  final SettingsProviderOption option;
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
    required this.providerOptions,
    required this.visibleOptionOrder,
    required this.visibleProviderLabels,
    required this.isFineGrainedTokenVisible,
    required this.isRepositoryPathVisible,
    required this.isWriteBranchVisible,
    required this.repositoryPathValue,
    required this.writeBranchValue,
    required this.isRepositoryPathReadOnly,
    required this.isWriteBranchReadOnly,
    this.repositoryPathTop,
    this.repositoryPathBottom,
    this.repositoryPathLeft,
    this.writeBranchTop,
    this.writeBranchBottom,
    this.writeBranchLeft,
  });

  final bool isProjectSettingsVisible;
  final Map<SettingsProviderOption, ProviderOptionState> providerOptions;
  final List<SettingsProviderOption> visibleOptionOrder;
  final List<String> visibleProviderLabels;
  final bool isFineGrainedTokenVisible;
  final bool isRepositoryPathVisible;
  final bool isWriteBranchVisible;
  final String? repositoryPathValue;
  final String? writeBranchValue;
  final bool isRepositoryPathReadOnly;
  final bool isWriteBranchReadOnly;
  final double? repositoryPathTop;
  final double? repositoryPathBottom;
  final double? repositoryPathLeft;
  final double? writeBranchTop;
  final double? writeBranchBottom;
  final double? writeBranchLeft;

  ProviderOptionState get hostedOption =>
      providerOptions[SettingsProviderOption.hosted]!;

  ProviderOptionState get connectGitHubOption => hostedOption;

  ProviderOptionState get localGitOption =>
      providerOptions[SettingsProviderOption.localGit]!;

  ProviderOptionState optionState(SettingsProviderOption option) =>
      providerOptions[option]!;
}
