import 'dart:convert';

import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../core/interfaces/workspace_profile_store_persistence_probe.dart';
import '../../core/models/workspace_profile_store_persistence_observation.dart';

class WorkspaceProfileStorePersistenceInspector
    implements WorkspaceProfileStorePersistenceProbe {
  WorkspaceProfileStorePersistenceInspector({
    required WorkspaceProfileService service,
    required Future<void> Function() resetState,
    required Future<String?> Function() readRawState,
  }) : _service = service,
       _resetState = resetState,
       _readRawState = readRawState;

  final WorkspaceProfileService _service;
  final Future<void> Function() _resetState;
  final Future<String?> Function() _readRawState;

  @override
  Future<WorkspaceProfileStorePersistenceObservation> observeHostedPersistence({
    required String repository,
    required String firstDefaultBranch,
    required String secondDefaultBranch,
  }) async {
    await _resetState();
    final initialStorageValue = await _readRawState();

    final firstProfile = await _service.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: repository,
        defaultBranch: firstDefaultBranch,
      ),
    );
    final afterFirstCreate = _readSnapshot(
      await _requireRawState('first hosted workspace profile creation'),
    );

    final secondProfile = await _service.createProfile(
      WorkspaceProfileInput(
        targetType: WorkspaceProfileTargetType.hosted,
        target: repository,
        defaultBranch: secondDefaultBranch,
      ),
    );
    final afterSecondCreate = _readSnapshot(
      await _requireRawState('second hosted workspace profile creation'),
    );

    return WorkspaceProfileStorePersistenceObservation(
      initialStorageValue: initialStorageValue,
      firstProfile: firstProfile,
      secondProfile: secondProfile,
      afterFirstCreate: afterFirstCreate,
      afterSecondCreate: afterSecondCreate,
    );
  }

  Future<String> _requireRawState(String operation) async {
    final rawJson = await _readRawState();
    if (rawJson == null || rawJson.isEmpty) {
      throw StateError(
        'WorkspaceProfileStore did not persist $workspaceProfileStorePersistenceStorageKey after $operation.',
      );
    }
    return rawJson;
  }

  WorkspaceProfileStoreSnapshot _readSnapshot(String rawJson) {
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
