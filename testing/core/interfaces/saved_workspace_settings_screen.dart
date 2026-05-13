import '../models/saved_workspace_settings_state.dart';

abstract interface class SavedWorkspaceSettingsScreenHandle {
  Future<void> open();

  Future<void> requestWorkspaceDeletion(String displayName);

  Future<void> confirmDeletion();

  SavedWorkspaceSettingsState captureState();

  void dispose();
}
