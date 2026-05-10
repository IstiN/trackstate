import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_reassignment_driver.dart';
import 'trackstate_test_runtime.dart';

class FlutterIssueReassignmentDriver implements IssueReassignmentDriver {
  FlutterIssueReassignmentDriver(this._tester);

  final WidgetTester _tester;

  @override
  Future<IssueMutationResult<TrackStateIssue>> reassignIssue({
    required String repositoryPath,
    required String issueKey,
    String? parentKey,
    String? epicKey,
  }) async {
    final repository = await createLocalGitMutationRepository(
      tester: _tester,
      repositoryPath: repositoryPath,
    );
    final result = await _tester.runAsync(
      () => IssueMutationService(repository: repository).reassignIssue(
        issueKey: issueKey,
        parentKey: parentKey,
        epicKey: epicKey,
      ),
    );
    if (result == null) {
      throw StateError('Issue reassignment did not complete.');
    }
    return result;
  }
}
