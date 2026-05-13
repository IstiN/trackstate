import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
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

class WorkspaceProfileStorePersistenceInspector {
  const WorkspaceProfileStorePersistenceInspector({DateTime Function()? now})
    : _now = now;

  static const storageKey = 'trackstate.workspaceProfiles.state';

  final DateTime Function()? _now;

  Future<WorkspaceProfileStorePersistenceObservation> observeHostedPersistence({
    required String repository,
    required String firstDefaultBranch,
    required String secondDefaultBranch,
  }) async {
    final preferences = await SharedPreferences.getInstance();
    final initialStorageValue = preferences.getString(storageKey);
    final service = SharedPreferencesWorkspaceProfileService(now: _now);

    final firstProfile = await service.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: repository,
        defaultBranch: firstDefaultBranch,
      ),
    );
    final afterFirstCreate = _readSnapshot(preferences);

    final secondProfile = await service.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: repository,
        defaultBranch: secondDefaultBranch,
      ),
    );
    final afterSecondCreate = _readSnapshot(preferences);

    return WorkspaceProfileStorePersistenceObservation(
      initialStorageValue: initialStorageValue,
      firstProfile: firstProfile,
      secondProfile: secondProfile,
      afterFirstCreate: afterFirstCreate,
      afterSecondCreate: afterSecondCreate,
    );
  }

  WorkspaceProfileStoreSnapshot _readSnapshot(SharedPreferences preferences) {
    final rawJson = preferences.getString(storageKey) ?? '';
    final decoded = jsonDecode(rawJson);
    if (decoded is! Map) {
      throw StateError(
        'WorkspaceProfileStore serialized state must decode to a JSON object.',
      );
    }

    final state = _stringKeyedMap(decoded);
    final rawProfiles = state['profiles'];
    final profiles = rawProfiles is List
        ? rawProfiles
              .whereType<Map>()
              .map<Map<String, Object?>>(_stringKeyedMap)
              .toList(growable: false)
        : const <Map<String, Object?>>[];

    return WorkspaceProfileStoreSnapshot(
      rawJson: rawJson,
      state: state,
      profiles: profiles,
      activeWorkspaceId: state['activeWorkspaceId']?.toString(),
      migrationComplete: state['migrationComplete'] == true,
    );
  }

  Map<String, Object?> _stringKeyedMap(Map<Object?, Object?> source) {
    return <String, Object?>{
      for (final entry in source.entries) '${entry.key}': entry.value,
    };
  }
}
