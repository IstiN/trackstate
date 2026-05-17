class WorkspaceProfileDeletionObservation {
  const WorkspaceProfileDeletionObservation({
    required this.remainingWorkspaceId,
    required this.remainingWorkspaceDisplayName,
    required this.deletedWorkspaceId,
    required this.deletedWorkspaceDisplayName,
    required this.activeBeforeDelete,
    required this.activeAfterDelete,
    required this.remainingWorkspaces,
    required this.workspaceTokenKeysBeforeDelete,
    required this.workspaceTokenKeysAfterDelete,
    required this.deletedWorkspaceTokenAfterDelete,
    required this.fallbackWorkspaceToken,
  });

  final String remainingWorkspaceId;
  final String remainingWorkspaceDisplayName;
  final String deletedWorkspaceId;
  final String deletedWorkspaceDisplayName;
  final String activeBeforeDelete;
  final String activeAfterDelete;
  final List<String> remainingWorkspaces;
  final List<String> workspaceTokenKeysBeforeDelete;
  final List<String> workspaceTokenKeysAfterDelete;
  final String? deletedWorkspaceTokenAfterDelete;
  final String? fallbackWorkspaceToken;
}
