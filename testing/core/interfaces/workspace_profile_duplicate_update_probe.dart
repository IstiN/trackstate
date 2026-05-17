import '../models/workspace_profile_duplicate_update_observation.dart';

abstract interface class WorkspaceProfileDuplicateUpdateProbe {
  Future<WorkspaceProfileDuplicateUpdateObservation> runScenario();
}
