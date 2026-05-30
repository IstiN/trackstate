import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueArchiveMutationPort {
  Future<IssueMutationResult<TrackStateIssue>> archiveIssue({
    required String repositoryPath,
    required String issueKey,
  });
}
