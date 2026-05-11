import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_link_mutation_driver.dart';
import 'trackstate_test_runtime.dart';

class FlutterIssueLinkMutationDriver implements IssueLinkMutationDriver {
  FlutterIssueLinkMutationDriver(this._tester);

  final WidgetTester _tester;

  @override
  Future<IssueMutationResult<TrackStateIssue>> createLink({
    required String repositoryPath,
    required String issueKey,
    required String targetKey,
    required String type,
  }) async {
    final repository = await createLocalGitMutationRepository(
      tester: _tester,
      repositoryPath: repositoryPath,
    );
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
}
