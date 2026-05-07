import 'package:trackstate/data/providers/local/local_git_trackstate_provider.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_deletion_port.dart';

class Ts66IssueDeletionPort implements IssueDeletionPort {
  Ts66IssueDeletionPort({
    required LocalTrackStateRepository repository,
    required String repositoryPath,
  }) : _repository = repository,
       _provider = LocalGitTrackStateProvider(repositoryPath: repositoryPath);

  final LocalTrackStateRepository _repository;
  final LocalGitTrackStateProvider _provider;

  @override
  Future<TrackerSnapshot> loadSnapshot() => _repository.loadSnapshot();

  @override
  Future<RepositoryPermission> getPermission() => _provider.getPermission();

  @override
  Future<String> resolveWriteBranch() => _provider.resolveWriteBranch();

  @override
  Future<List<RepositoryTreeEntry>> listTree({required String ref}) =>
      _provider.listTree(ref: ref);

  @override
  Future<RepositoryTextFile> readTextFile(String path, {required String ref}) =>
      _provider.readTextFile(path, ref: ref);

  @override
  Future<RepositoryWriteResult> writeTextFile(RepositoryWriteRequest request) =>
      _provider.writeTextFile(request);
}
