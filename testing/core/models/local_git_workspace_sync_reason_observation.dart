import 'package:trackstate/domain/models/trackstate_models.dart';

class LocalGitWorkspaceSyncReasonObservation {
  const LocalGitWorkspaceSyncReasonObservation({
    required this.repositoryPath,
    required this.issuePath,
    required this.initialHeadRevision,
    required this.headChangeRevision,
    required this.headChangeCommitSubject,
    required this.headCheck,
    required this.worktreeStatusLines,
    required this.worktreeCheck,
  });

  final String repositoryPath;
  final String issuePath;
  final String initialHeadRevision;
  final String headChangeRevision;
  final String headChangeCommitSubject;
  final LocalGitWorkspaceSyncCheckObservation headCheck;
  final List<String> worktreeStatusLines;
  final LocalGitWorkspaceSyncCheckObservation worktreeCheck;
}

class LocalGitWorkspaceSyncCheckObservation {
  const LocalGitWorkspaceSyncCheckObservation({
    required this.result,
    required this.statusHealth,
    required this.reasons,
    required this.refreshTriggered,
  });

  final WorkspaceSyncResult result;
  final WorkspaceSyncHealth statusHealth;
  final List<String> reasons;
  final bool refreshTriggered;

  Set<WorkspaceSyncDomain> get changedDomains => result.changedDomains;

  Set<String> get changedPaths => {
    for (final domain in result.domains.values) ...domain.paths,
  };

  Set<String> get issueKeys => {
    for (final domain in result.domains.values) ...domain.issueKeys,
  };
}
