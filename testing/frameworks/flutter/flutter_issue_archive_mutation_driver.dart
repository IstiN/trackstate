import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_archive_mutation_driver.dart';
import 'trackstate_test_runtime.dart';

class FlutterIssueArchiveMutationDriver implements IssueArchiveMutationDriver {
  FlutterIssueArchiveMutationDriver(this._tester);

  final WidgetTester _tester;

  @override
  Future<IssueMutationResult<TrackStateIssue>> archiveIssue({
    required String repositoryPath,
    required String issueKey,
  }) async {
    final repository = await createLocalGitMutationRepository(
      tester: _tester,
      repositoryPath: repositoryPath,
    );
    final result = await _tester.runAsync(
      () => IssueMutationService(repository: repository).archiveIssue(issueKey),
    );
    if (result == null) {
      throw StateError('Issue archive mutation did not complete.');
    }
    return result;
  }
}
