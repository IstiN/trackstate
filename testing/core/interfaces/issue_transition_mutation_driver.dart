import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueTransitionMutationDriver {
  Future<IssueMutationResult<TrackStateIssue>> transitionIssue({
    required String repositoryPath,
    required String issueKey,
    required String status,
  });
}
