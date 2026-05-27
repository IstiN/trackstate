import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueLinkMutationDriver {
  Future<IssueMutationResult<TrackStateIssue>> createLink({
    required String repositoryPath,
    required String issueKey,
    required String targetKey,
    required String type,
  });
}
