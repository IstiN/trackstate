import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_transition_mutation_driver.dart';
import 'trackstate_test_runtime.dart';

class FlutterIssueTransitionMutationDriver
    implements IssueTransitionMutationDriver {
  FlutterIssueTransitionMutationDriver(this._tester);

  final WidgetTester _tester;

  @override
  Future<IssueMutationResult<TrackStateIssue>> transitionIssue({
    required String repositoryPath,
    required String issueKey,
    required String status,
  }) async {
    final repository = await createLocalGitMutationRepository(
      tester: _tester,
      repositoryPath: repositoryPath,
    );
    final result = await _tester.runAsync(
      () => IssueMutationService(
        repository: repository,
      ).transitionIssue(issueKey: issueKey, status: status),
    );
    if (result == null) {
      throw StateError('Issue transition mutation did not complete.');
    }
    return result;
  }
}
