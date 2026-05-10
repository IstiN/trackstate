import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_link_mutation_port.dart';

class IssueLinkMutationService implements IssueLinkMutationPort {
  IssueLinkMutationService(this._tester);

  final WidgetTester _tester;

  @override
  Future<IssueMutationResult<TrackStateIssue>> createLink({
    required String repositoryPath,
    required String issueKey,
    required String targetKey,
    required String type,
  }) async {
    final repository = await _openRepository(repositoryPath: repositoryPath);
    final result = await _tester.runAsync(
      () => IssueMutationService(
        repository: repository,
      ).createLink(issueKey: issueKey, targetKey: targetKey, type: type),
    );
    if (result == null) {
      throw StateError('Issue link mutation did not complete.');
    }
    return result;
  }

  Future<TrackStateRepository> _openRepository({
    required String repositoryPath,
  }) async {
    final repository = createTrackStateRepository(
      runtime: TrackStateRuntime.localGit,
      localRepositoryPath: repositoryPath,
    );
    final snapshot = await _tester.runAsync(repository.loadSnapshot);
    if (snapshot == null) {
      throw StateError('Local Git snapshot loading did not complete.');
    }
    final user = await _tester.runAsync(
      () => repository.connect(
        RepositoryConnection(
          repository: snapshot.project.repository,
          branch: snapshot.project.branch,
          token: '',
        ),
      ),
    );
    if (user == null) {
      throw StateError('Local Git user resolution did not complete.');
    }
    return repository;
  }
}
