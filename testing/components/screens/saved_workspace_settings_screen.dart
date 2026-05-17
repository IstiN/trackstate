import '../../core/interfaces/saved_workspace_settings_driver.dart';
import '../../core/interfaces/saved_workspace_settings_screen.dart';
import '../../core/models/saved_workspace_settings_state.dart';

class SavedWorkspaceSettingsScreen
    implements SavedWorkspaceSettingsScreenHandle {
  const SavedWorkspaceSettingsScreen({
    required SavedWorkspaceSettingsDriver driver,
    required void Function() onDispose,
  }) : _driver = driver,
       _onDispose = onDispose;

  final SavedWorkspaceSettingsDriver _driver;
  final void Function() _onDispose;

  @override
  Future<void> open() => _driver.openSettings();

  @override
  Future<void> requestWorkspaceDeletion(String displayName) =>
      _driver.tapWorkspaceDelete(displayName);

  @override
  Future<void> confirmDeletion() => _driver.tapDialogAction('Delete');

  @override
  SavedWorkspaceSettingsState captureState() => _driver.captureState();

  @override
  void dispose() => _onDispose();
}
