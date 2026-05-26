import 'package:trackstate/domain/models/workspace_profile_models.dart';

class WorkspaceProfileStoreSnapshot {
  const WorkspaceProfileStoreSnapshot({
    required this.rawJson,
    required this.state,
    required this.profiles,
    required this.activeWorkspaceId,
    required this.migrationComplete,
  });

  final String rawJson;
  final Map<String, Object?> state;
  final List<Map<String, Object?>> profiles;
  final String? activeWorkspaceId;
  final bool migrationComplete;

  Map<String, Object?>? profileById(String workspaceId) {
    for (final profile in profiles) {
      if ('${profile['id'] ?? ''}' == workspaceId) {
        return profile;
      }
    }
    return null;
  }
}

class WorkspaceProfileStorePersistenceObservation {
  const WorkspaceProfileStorePersistenceObservation({
    required this.initialStorageValue,
    required this.firstProfile,
    required this.secondProfile,
    required this.afterFirstCreate,
    required this.afterSecondCreate,
  });

  final String? initialStorageValue;
  final WorkspaceProfile firstProfile;
  final WorkspaceProfile secondProfile;
  final WorkspaceProfileStoreSnapshot afterFirstCreate;
  final WorkspaceProfileStoreSnapshot afterSecondCreate;
}
