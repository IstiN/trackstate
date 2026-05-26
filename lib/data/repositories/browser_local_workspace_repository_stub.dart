import 'trackstate_repository.dart';

Future<TrackStateRepository?> openBrowserLocalWorkspaceRepository({
  required String repositoryPath,
  required String defaultBranch,
  required String writeBranch,
}) async => null;

Future<TrackStateRepository?> requestBrowserLocalWorkspaceRepositoryAccess({
  required String repositoryPath,
  required String defaultBranch,
  required String writeBranch,
}) async => null;

void rememberBrowserLocalWorkspaceSelection({
  required String workspacePath,
  required Object selection,
}) {}
