import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class IssueReassignmentDriver {
  Future<IssueMutationResult<TrackStateIssue>> reassignIssue({
    required String repositoryPath,
    required String issueKey,
    String? parentKey,
    String? epicKey,
  });
}
