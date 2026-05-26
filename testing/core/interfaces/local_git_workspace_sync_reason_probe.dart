import '../models/local_git_workspace_sync_reason_observation.dart';

abstract interface class LocalGitWorkspaceSyncReasonProbe {
  Future<LocalGitWorkspaceSyncReasonObservation> runScenario();
}
