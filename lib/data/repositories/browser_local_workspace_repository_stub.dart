import 'trackstate_repository.dart';

Future<TrackStateRepository?> openBrowserLocalWorkspaceRepository({
  required String repositoryPath,
  required String defaultBranch,
  required String writeBranch,
}) async => null;

Future<void> rememberBrowserLocalWorkspaceSelection({
  required String workspacePath,
  required Object selection,
}) async {}

Future<void> debugResetBrowserLocalWorkspaceSelectionCache({
  bool clearPersisted = false,
}) async {}
