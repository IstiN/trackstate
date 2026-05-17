import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/local_git_repository_factory.dart';

class ProviderBackedLocalGitRepositoryFactory
    implements LocalGitRepositoryFactory {
  const ProviderBackedLocalGitRepositoryFactory();

  @override
  Future<TrackStateRepository> create({required String repositoryPath}) async {
    final repository = ProviderBackedTrackStateRepository(
      provider: LocalGitTrackStateProvider(repositoryPath: repositoryPath),
      usesLocalPersistence: true,
      supportsGitHubAuth: false,
    );
    final snapshot = await repository.loadSnapshot();
    await repository.connect(
      RepositoryConnection(
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        token: '',
      ),
    );
    return repository;
  }
}
