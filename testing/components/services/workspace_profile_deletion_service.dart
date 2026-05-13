import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../core/interfaces/workspace_profile_deletion_probe.dart';
import '../../core/models/workspace_profile_deletion_observation.dart';

class WorkspaceProfileDeletionService implements WorkspaceProfileDeletionProbe {
  const WorkspaceProfileDeletionService({
    required WorkspaceProfileService workspaceProfileService,
    required TrackStateAuthStore authStore,
  }) : _workspaceProfileService = workspaceProfileService,
       _authStore = authStore;

  final WorkspaceProfileService _workspaceProfileService;
  final TrackStateAuthStore _authStore;

  @override
  Future<WorkspaceProfileDeletionObservation> inspectActiveWorkspaceDeletion({
    required WorkspaceProfileInput remainingProfileInput,
    required WorkspaceProfileInput deletedActiveProfileInput,
    required String deletedActiveProfileToken,
  }) async {
    final remainingWorkspace = await _workspaceProfileService.createProfile(
      remainingProfileInput,
    );
    final deletedWorkspace = await _workspaceProfileService.createProfile(
      deletedActiveProfileInput,
    );
    await _authStore.saveToken(
      deletedActiveProfileToken,
      workspaceId: deletedWorkspace.id,
    );

    final stateBeforeDelete = await _workspaceProfileService.loadState();
    final preferencesBeforeDelete = await SharedPreferences.getInstance();
    final workspaceTokenKeysBeforeDelete = _workspaceTokenKeys(
      preferencesBeforeDelete,
    );

    final nextState = await _workspaceProfileService.deleteProfile(
      deletedWorkspace.id,
    );
    final persistedState = await _workspaceProfileService.loadState();
    final preferencesAfterDelete = await SharedPreferences.getInstance();
    final workspaceTokenKeysAfterDelete = _workspaceTokenKeys(
      preferencesAfterDelete,
    );
    final deletedWorkspaceTokenAfterDelete = await _authStore.readToken(
      workspaceId: deletedWorkspace.id,
    );
    final fallbackWorkspaceToken = await _authStore.readToken(
      workspaceId: remainingWorkspace.id,
    );

    return WorkspaceProfileDeletionObservation(
      remainingWorkspaceId: remainingWorkspace.id,
      remainingWorkspaceDisplayName: remainingWorkspace.displayName,
      deletedWorkspaceId: deletedWorkspace.id,
      deletedWorkspaceDisplayName: deletedWorkspace.displayName,
      activeBeforeDelete: stateBeforeDelete.activeWorkspaceId ?? '',
      activeAfterDelete: persistedState.activeWorkspaceId ?? '',
      remainingWorkspaces: nextState.profiles
          .map((profile) => profile.displayName)
          .toList(growable: false),
      workspaceTokenKeysBeforeDelete: workspaceTokenKeysBeforeDelete,
      workspaceTokenKeysAfterDelete: workspaceTokenKeysAfterDelete,
      deletedWorkspaceTokenAfterDelete: deletedWorkspaceTokenAfterDelete,
      fallbackWorkspaceToken: fallbackWorkspaceToken,
    );
  }

  List<String> _workspaceTokenKeys(SharedPreferences preferences) {
    final keys = preferences.getKeys().where((key) {
      return key.startsWith('trackstate.githubToken.workspace.');
    }).toList()..sort();
    return keys;
  }
}
