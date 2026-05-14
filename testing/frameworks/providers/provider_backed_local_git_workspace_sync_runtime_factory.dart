import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_sync_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/local_git_repository_factory.dart';
import '../../core/interfaces/local_git_workspace_sync_runtime.dart';
import '../../core/interfaces/local_git_workspace_sync_runtime_factory.dart';
import 'provider_backed_local_git_repository_factory.dart';

class ProviderBackedLocalGitWorkspaceSyncRuntimeFactory
    implements LocalGitWorkspaceSyncRuntimeFactory {
  const ProviderBackedLocalGitWorkspaceSyncRuntimeFactory({
    LocalGitRepositoryFactory repositoryFactory =
        const ProviderBackedLocalGitRepositoryFactory(),
  }) : _repositoryFactory = repositoryFactory;

  final LocalGitRepositoryFactory _repositoryFactory;

  @override
  Future<LocalGitWorkspaceSyncRuntime> create({
    required String repositoryPath,
  }) async {
    final repository = await _repositoryFactory.create(
      repositoryPath: repositoryPath,
    );
    if (repository case final WorkspaceSyncRepository syncRepository) {
      return _ProviderBackedLocalGitWorkspaceSyncRuntime(
        repository: repository,
        syncRepository: syncRepository,
      );
    }
    throw StateError(
      'Local Git workspace sync runtime requires a repository that implements WorkspaceSyncRepository.',
    );
  }
}

class _ProviderBackedLocalGitWorkspaceSyncRuntime
    implements LocalGitWorkspaceSyncRuntime {
  _ProviderBackedLocalGitWorkspaceSyncRuntime({
    required TrackStateRepository repository,
    required WorkspaceSyncRepository syncRepository,
  }) : _repository = repository {
    _service = WorkspaceSyncService(
      repository: syncRepository,
      loadSnapshot: repository.loadSnapshot,
      onRefresh: (_) => _refreshCount += 1,
      onStatusChanged: (_) {},
    );
  }

  final TrackStateRepository _repository;
  late final WorkspaceSyncService _service;
  int _refreshCount = 0;

  @override
  Future<TrackerSnapshot> loadSnapshot() => _repository.loadSnapshot();

  @override
  void updateBaselineSnapshot(TrackerSnapshot snapshot) {
    _service.updateBaselineSnapshot(snapshot);
  }

  @override
  Future<void> checkNow({bool force = false}) =>
      _service.checkNow(force: force);

  @override
  WorkspaceSyncStatus get status => _service.status;

  @override
  int get refreshCount => _refreshCount;

  @override
  void dispose() {
    _service.dispose();
  }
}
