class WorkspaceOnboardingChoiceObservation {
  const WorkspaceOnboardingChoiceObservation({
    required this.isLocalFolderVisible,
    required this.isHostedRepositoryVisible,
    required this.localFolderHasSemanticLabel,
    required this.hostedRepositoryHasSemanticLabel,
    required this.sharedChoiceRow,
    required this.verticalCenterDelta,
    required this.horizontalGap,
    required this.widthDelta,
    required this.heightDelta,
    required this.localFolderRect,
    required this.hostedRepositoryRect,
  });

  final bool isLocalFolderVisible;
  final bool isHostedRepositoryVisible;
  final bool localFolderHasSemanticLabel;
  final bool hostedRepositoryHasSemanticLabel;
  final bool sharedChoiceRow;
  final double? verticalCenterDelta;
  final double? horizontalGap;
  final double? widthDelta;
  final double? heightDelta;
  final Map<String, double>? localFolderRect;
  final Map<String, double>? hostedRepositoryRect;

  bool get hasEqualFirstClassChoices {
    final verticalCenterDelta = this.verticalCenterDelta;
    final horizontalGap = this.horizontalGap;
    final widthDelta = this.widthDelta;
    final heightDelta = this.heightDelta;
    return isLocalFolderVisible &&
        isHostedRepositoryVisible &&
        localFolderHasSemanticLabel &&
        hostedRepositoryHasSemanticLabel &&
        sharedChoiceRow &&
        verticalCenterDelta != null &&
        horizontalGap != null &&
        widthDelta != null &&
        heightDelta != null &&
        verticalCenterDelta <= 4 &&
        horizontalGap >= 0 &&
        widthDelta <= 4 &&
        heightDelta <= 4;
  }

  Map<String, Object?> toJson() => <String, Object?>{
    'is_local_folder_visible': isLocalFolderVisible,
    'is_hosted_repository_visible': isHostedRepositoryVisible,
    'local_folder_has_semantic_label': localFolderHasSemanticLabel,
    'hosted_repository_has_semantic_label': hostedRepositoryHasSemanticLabel,
    'shared_choice_row': sharedChoiceRow,
    'vertical_center_delta': verticalCenterDelta,
    'horizontal_gap': horizontalGap,
    'width_delta': widthDelta,
    'height_delta': heightDelta,
    'local_folder_rect': localFolderRect,
    'hosted_repository_rect': hostedRepositoryRect,
  };
}
