import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../../components/services/workspace_profile_store_persistence_inspector.dart';
import '../../../core/interfaces/workspace_profile_store_persistence_probe.dart';

WorkspaceProfileStorePersistenceProbe
createWorkspaceProfileStorePersistenceProbe({DateTime Function()? now}) {
  return WorkspaceProfileStorePersistenceInspector(
    service: SharedPreferencesWorkspaceProfileService(now: now),
    resetState: _resetWorkspaceProfileStoreState,
    readRawState: _readWorkspaceProfileStoreRawState,
  );
}

Future<void> _resetWorkspaceProfileStoreState() async {
  SharedPreferences.setMockInitialValues(const <String, Object>{});
}

Future<String?> _readWorkspaceProfileStoreRawState() async {
  final preferences = await SharedPreferences.getInstance();
  return preferences.getString(workspaceProfileStorePersistenceStorageKey);
}
