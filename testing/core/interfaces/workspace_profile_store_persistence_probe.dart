import '../models/workspace_profile_store_persistence_observation.dart';

const String workspaceProfileStorePersistenceStorageKey =
    'trackstate.workspaceProfiles.state';

abstract interface class WorkspaceProfileStorePersistenceProbe {
  Future<WorkspaceProfileStorePersistenceObservation> observeHostedPersistence({
    required String repository,
    required String firstDefaultBranch,
    required String secondDefaultBranch,
  });
}
