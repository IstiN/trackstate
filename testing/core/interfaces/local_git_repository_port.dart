import 'package:trackstate/data/repositories/trackstate_repository.dart';

abstract interface class LocalGitRepositoryPort {
  Future<TrackStateRepository> openRepository({
    required String repositoryPath,
    Duration initialAppLoadDelay = Duration.zero,
  });
}
