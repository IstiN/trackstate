import 'local_git_workspace_sync_runtime.dart';

abstract interface class LocalGitWorkspaceSyncRuntimeFactory {
  Future<LocalGitWorkspaceSyncRuntime> create({required String repositoryPath});
}
