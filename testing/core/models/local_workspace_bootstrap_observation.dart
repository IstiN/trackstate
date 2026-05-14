class LocalWorkspaceBootstrapObservation {
  const LocalWorkspaceBootstrapObservation({
    required this.targetFolderPath,
    required this.workspaceName,
    required this.writeBranch,
    required this.inspectionState,
    required this.inspectionMessage,
    required this.suggestedWorkspaceName,
    required this.needsGitInitialization,
    required this.hasGitRepository,
    required this.projectKey,
    required this.projectJson,
    required this.nonGitFilePaths,
    required this.directoryTree,
    required this.gitattributesContent,
    required this.issuesIndexContent,
    required this.tombstonesIndexContent,
    required this.gitLogOutput,
    required this.gitCommitMessages,
    required this.gitCommitCount,
    required this.gitHeadBranch,
  });

  final String targetFolderPath;
  final String workspaceName;
  final String writeBranch;
  final String inspectionState;
  final String inspectionMessage;
  final String suggestedWorkspaceName;
  final bool needsGitInitialization;
  final bool hasGitRepository;
  final String projectKey;
  final Map<String, Object?> projectJson;
  final List<String> nonGitFilePaths;
  final String directoryTree;
  final String gitattributesContent;
  final String issuesIndexContent;
  final String tombstonesIndexContent;
  final String gitLogOutput;
  final List<String> gitCommitMessages;
  final int gitCommitCount;
  final String gitHeadBranch;
}
