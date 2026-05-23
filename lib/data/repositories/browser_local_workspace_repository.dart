import 'trackstate_repository.dart';
import 'browser_local_workspace_repository_stub.dart'
    if (dart.library.js_interop) 'browser_local_workspace_repository_web.dart'
    as platform;

Future<TrackStateRepository?> openBrowserLocalWorkspaceRepository({
  required String repositoryPath,
  required String defaultBranch,
  required String writeBranch,
}) {
  return platform.openBrowserLocalWorkspaceRepository(
    repositoryPath: repositoryPath,
    defaultBranch: defaultBranch,
    writeBranch: writeBranch,
  );
}

void rememberBrowserLocalWorkspaceSelection({
  required String workspacePath,
  required Object selection,
}) {
  platform.rememberBrowserLocalWorkspaceSelection(
    workspacePath: workspacePath,
    selection: selection,
  );
}
