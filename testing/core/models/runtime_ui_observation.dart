class RuntimeUiObservation {
  const RuntimeUiObservation({
    required this.repositoryAccessVisible,
    required this.connectGitHubDialogVisible,
    required this.fineGrainedTokenVisible,
    required this.fineGrainedTokenHelperVisible,
    required this.rememberOnThisBrowserVisible,
    required this.localRuntimeMessagingVisible,
  });

  final bool repositoryAccessVisible;
  final bool connectGitHubDialogVisible;
  final bool fineGrainedTokenVisible;
  final bool fineGrainedTokenHelperVisible;
  final bool rememberOnThisBrowserVisible;
  final bool localRuntimeMessagingVisible;

  bool get matchesHostedRuntimeExperience =>
      repositoryAccessVisible &&
      connectGitHubDialogVisible &&
      fineGrainedTokenVisible &&
      fineGrainedTokenHelperVisible &&
      rememberOnThisBrowserVisible &&
      localRuntimeMessagingVisible == false;
}
