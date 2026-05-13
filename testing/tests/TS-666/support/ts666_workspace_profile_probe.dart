import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../../components/services/workspace_profile_duplicate_target_validator.dart';
import '../../../core/interfaces/workspace_profile_duplicate_target_probe.dart';

WorkspaceProfileDuplicateTargetProbe
createWorkspaceProfileDuplicateTargetProbe() {
  return WorkspaceProfileDuplicateTargetValidator(
    service: SharedPreferencesWorkspaceProfileService(
      authStore: const _MemoryTrackStateAuthStore(),
    ),
    resetState: _resetWorkspaceProfileState,
  );
}

Future<void> _resetWorkspaceProfileState() async {
  SharedPreferences.setMockInitialValues(const <String, Object>{});
}

class _MemoryTrackStateAuthStore implements TrackStateAuthStore {
  const _MemoryTrackStateAuthStore();

  @override
  Future<void> clearToken({String? repository, String? workspaceId}) async {}

  @override
  Future<String?> migrateLegacyRepositoryToken({
    required String repository,
    required String workspaceId,
  }) async => null;

  @override
  Future<void> moveToken({
    required String fromWorkspaceId,
    required String toWorkspaceId,
  }) async {}

  @override
  Future<String?> readToken({String? repository, String? workspaceId}) async =>
      null;

  @override
  Future<void> saveToken(
    String token, {
    String? repository,
    String? workspaceId,
  }) async {}
}
