import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

class Ts721RecordingWorkspaceProfileService implements WorkspaceProfileService {
  Ts721RecordingWorkspaceProfileService(this._delegate);

  final WorkspaceProfileService _delegate;
  final List<WorkspaceProfileInput> createdInputs = <WorkspaceProfileInput>[];
  final List<bool> createSelectValues = <bool>[];
  final List<String> selectedWorkspaceIds = <String>[];

  @override
  Future<WorkspaceProfile> createProfile(
    WorkspaceProfileInput input, {
    bool select = true,
  }) async {
    createdInputs.add(input);
    createSelectValues.add(select);
    return _delegate.createProfile(input, select: select);
  }

  @override
  Future<WorkspaceProfilesState> deleteProfile(String workspaceId) =>
      _delegate.deleteProfile(workspaceId);

  @override
  Future<WorkspaceProfile?> ensureLegacyContextMigrated(
    WorkspaceProfileInput? input,
  ) => _delegate.ensureLegacyContextMigrated(input);

  @override
  Future<WorkspaceProfilesState> loadState() => _delegate.loadState();

  @override
  Future<WorkspaceProfilesState> saveHostedAccessMode(
    String workspaceId,
    HostedWorkspaceAccessMode? accessMode,
  ) => _delegate.saveHostedAccessMode(workspaceId, accessMode);

  @override
  Future<WorkspaceProfilesState> selectProfile(String workspaceId) async {
    selectedWorkspaceIds.add(workspaceId);
    return _delegate.selectProfile(workspaceId);
  }

  @override
  Future<WorkspaceProfile> updateProfile(
    String workspaceId,
    WorkspaceProfileInput input, {
    bool select = true,
  }) => _delegate.updateProfile(workspaceId, input, select: select);
}
