import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_reassignment_driver.dart';
import '../../core/interfaces/issue_reassignment_port.dart';

class IssueReassignmentService implements IssueReassignmentPort {
  IssueReassignmentService({
    required IssueReassignmentDriver reassignmentDriver,
  }) : _reassignmentDriver = reassignmentDriver;

  final IssueReassignmentDriver _reassignmentDriver;

  @override
  Future<IssueMutationResult<TrackStateIssue>> reassignIssue({
    required String repositoryPath,
    required String issueKey,
    String? parentKey,
    String? epicKey,
  }) async {
    return _reassignmentDriver.reassignIssue(
      repositoryPath: repositoryPath,
      issueKey: issueKey,
      parentKey: parentKey,
      epicKey: epicKey,
    );
  }
}
