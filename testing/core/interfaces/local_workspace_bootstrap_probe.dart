import '../models/local_workspace_bootstrap_observation.dart';

abstract interface class LocalWorkspaceBootstrapProbe {
  Future<LocalWorkspaceBootstrapObservation> runScenario({
    required String workspaceName,
    required String writeBranch,
  });
}
