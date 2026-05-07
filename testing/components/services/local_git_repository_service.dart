import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../frameworks/flutter/trackstate_test_runtime.dart';

class LocalGitRepositoryService {
  const LocalGitRepositoryService(this._tester);

  final WidgetTester _tester;

  Future<TrackStateRepository> openRepository({
    required String repositoryPath,
  }) {
    return createLocalGitTestRepository(
      tester: _tester,
      repositoryPath: repositoryPath,
    );
  }
}
