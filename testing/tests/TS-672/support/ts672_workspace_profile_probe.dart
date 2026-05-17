import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../../components/services/workspace_profile_duplicate_update_validator.dart';
import '../../../core/interfaces/workspace_profile_duplicate_update_probe.dart';

WorkspaceProfileDuplicateUpdateProbe createTs672WorkspaceProfileProbe() {
  return WorkspaceProfileDuplicateUpdateValidator(
    service: SharedPreferencesWorkspaceProfileService(
      authStore: const _MemoryTrackStateAuthStore(),
      now: _SequencedNow(<DateTime>[
        DateTime.utc(2026, 5, 13, 22, 0, 0),
        DateTime.utc(2026, 5, 13, 22, 5, 0),
        DateTime.utc(2026, 5, 13, 22, 10, 0),
      ]).call,
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

class _SequencedNow {
  _SequencedNow(this._values);

  final List<DateTime> _values;
  var _index = 0;

  DateTime call() {
    if (_index >= _values.length) {
      return _values.last;
    }
    final value = _values[_index];
    _index += 1;
    return value;
  }
}
