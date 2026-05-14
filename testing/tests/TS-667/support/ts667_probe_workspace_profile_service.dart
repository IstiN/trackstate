import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

class Ts667ProbeWorkspaceProfileService implements WorkspaceProfileService {
  Ts667ProbeWorkspaceProfileService(this._state);

  WorkspaceProfilesState _state;
  final List<String> deletedWorkspaceIds = <String>[];

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) async {
    deletedWorkspaceIds.add(workspaceId);
    _state = WorkspaceProfilesState(
      profiles: _state.profiles
          .where((profile) => profile.id != workspaceId)
          .toList(growable: false),
      activeWorkspaceId: _state.activeWorkspaceId == workspaceId
          ? _state.profiles
                .where((profile) => profile.id != workspaceId)
                .firstOrNull
                ?.id
          : _state.activeWorkspaceId,
      migrationComplete: true,
    );
    return _state;
  }

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) async {
    _state = WorkspaceProfilesState(
      profiles: [
        for (final profile in _state.profiles)
          if (profile.id == workspaceId && profile.isHosted)
            profile.copyWith(hostedAccessMode: accessMode)
          else
            profile,
      ],
      activeWorkspaceId: _state.activeWorkspaceId,
      migrationComplete: _state.migrationComplete,
    );
    return _state;
  }

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) async => _state.activeWorkspace;

  @override
  Future<WorkspaceProfilesState> loadState() async => _state;

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    _state = _state.copyWith(activeWorkspaceId: workspaceId);
    return _state;
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) {
    throw UnimplementedError();
  }
}
