class RuntimeUiStabilityObservation {
  const RuntimeUiStabilityObservation({
    required this.connectGitHubElementCount,
    required this.connectGitHubStableAcrossPumps,
    required this.fineGrainedTokenElementCount,
    required this.fineGrainedTokenStableAcrossPumps,
    required this.fineGrainedTokenHelperElementCount,
    required this.fineGrainedTokenHelperStableAcrossPumps,
    required this.rememberOnThisBrowserElementCount,
    required this.rememberOnThisBrowserStableAcrossPumps,
  });

  final int connectGitHubElementCount;
  final bool connectGitHubStableAcrossPumps;
  final int fineGrainedTokenElementCount;
  final bool fineGrainedTokenStableAcrossPumps;
  final int fineGrainedTokenHelperElementCount;
  final bool fineGrainedTokenHelperStableAcrossPumps;
  final int rememberOnThisBrowserElementCount;
  final bool rememberOnThisBrowserStableAcrossPumps;

  /// The hierarchy is considered stable when the probed elements are present,
  /// their counts do not change across pump cycles, and the dialog descendants
  /// are unique.
  bool get isStableForAutomatedProbes =>
      connectGitHubElementCount > 0 &&
      connectGitHubStableAcrossPumps &&
      fineGrainedTokenElementCount == 1 &&
      fineGrainedTokenStableAcrossPumps &&
      fineGrainedTokenHelperElementCount == 1 &&
      fineGrainedTokenHelperStableAcrossPumps &&
      rememberOnThisBrowserElementCount == 1 &&
      rememberOnThisBrowserStableAcrossPumps;
}
