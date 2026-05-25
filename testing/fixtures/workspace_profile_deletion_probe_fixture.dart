import 'package:trackstate/data/services/trackstate_auth_store.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../components/services/workspace_profile_deletion_service.dart';
import '../core/interfaces/workspace_profile_deletion_probe.dart';

WorkspaceProfileDeletionProbe
createSharedPreferencesWorkspaceProfileDeletionProbe({
  required DateTime Function() now,
}) {
  const authStore = SharedPreferencesTrackStateAuthStore();
  return WorkspaceProfileDeletionService(
    workspaceProfileService: SharedPreferencesWorkspaceProfileService(
      authStore: authStore,
      now: now,
    ),
    authStore: authStore,
  );
}
