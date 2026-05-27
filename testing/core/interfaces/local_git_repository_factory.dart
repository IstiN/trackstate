import 'package:trackstate/data/repositories/trackstate_repository.dart';

abstract interface class LocalGitRepositoryFactory {
  Future<TrackStateRepository> create({required String repositoryPath});
}
