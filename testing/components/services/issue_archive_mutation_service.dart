import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_archive_mutation_driver.dart';
import '../../core/interfaces/issue_archive_mutation_port.dart';

class IssueArchiveMutationService implements IssueArchiveMutationPort {
  IssueArchiveMutationService({
    required IssueArchiveMutationDriver mutationDriver,
  }) : _mutationDriver = mutationDriver;

  final IssueArchiveMutationDriver _mutationDriver;

  @override
  Future<IssueMutationResult<TrackStateIssue>> archiveIssue({
    required String repositoryPath,
    required String issueKey,
  }) async {
    return _mutationDriver.archiveIssue(
      repositoryPath: repositoryPath,
      issueKey: issueKey,
    );
  }
}
