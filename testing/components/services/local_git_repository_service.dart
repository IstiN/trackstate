import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/interfaces/local_git_repository_port.dart';
import '../../frameworks/flutter/trackstate_test_runtime.dart';

class LocalGitRepositoryService implements LocalGitRepositoryPort {
  LocalGitRepositoryService(this._tester);

  final WidgetTester _tester;
  final Map<String, Future<TrackStateRepository>> _repositoriesByPath =
      <String, Future<TrackStateRepository>>{};

  @override
  Future<TrackStateRepository> openRepository({
    required String repositoryPath,
  }) {
    return _repositoriesByPath.putIfAbsent(repositoryPath, () {
      return createLocalGitTestRepository(
        tester: _tester,
        repositoryPath: repositoryPath,
      );
    });
  }
}
