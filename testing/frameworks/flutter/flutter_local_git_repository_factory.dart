import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../core/interfaces/local_git_repository_factory.dart';
import 'trackstate_test_runtime.dart';

class FlutterLocalGitRepositoryFactory implements LocalGitRepositoryFactory {
  FlutterLocalGitRepositoryFactory(this.tester);

  final WidgetTester tester;

  @override
  Future<TrackStateRepository> create({required String repositoryPath}) {
    return createLocalGitTestRepository(
      tester: tester,
      repositoryPath: repositoryPath,
    );
  }
}
