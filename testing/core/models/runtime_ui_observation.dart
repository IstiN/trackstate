class RuntimeUiObservation {
  const RuntimeUiObservation({
    required this.repositoryType,
    required this.usesLocalPersistence,
    required this.supportsGitHubAuth,
    required this.repositoryAccessVisible,
    required this.connectGitHubDialogVisible,
    required this.fineGrainedTokenVisible,
    required this.fineGrainedTokenHelperVisible,
    required this.rememberOnThisBrowserVisible,
    required this.localRuntimeMessagingVisible,
  });

  final String repositoryType;
  final bool usesLocalPersistence;
  final bool supportsGitHubAuth;
  final bool repositoryAccessVisible;
  final bool connectGitHubDialogVisible;
  final bool fineGrainedTokenVisible;
  final bool fineGrainedTokenHelperVisible;
  final bool rememberOnThisBrowserVisible;
  final bool localRuntimeMessagingVisible;

  bool get matchesHostedRuntimeExperience =>
      repositoryType == 'SetupTrackStateRepository' &&
      usesLocalPersistence == false &&
      supportsGitHubAuth &&
      repositoryAccessVisible &&
      connectGitHubDialogVisible &&
      fineGrainedTokenVisible &&
      fineGrainedTokenHelperVisible &&
      rememberOnThisBrowserVisible &&
      localRuntimeMessagingVisible == false;
}
