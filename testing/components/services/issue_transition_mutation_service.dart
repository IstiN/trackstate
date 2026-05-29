import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_transition_mutation_driver.dart';
import '../../core/interfaces/issue_transition_mutation_port.dart';

class IssueTransitionMutationService implements IssueTransitionMutationPort {
  IssueTransitionMutationService({
    required IssueTransitionMutationDriver mutationDriver,
  }) : _mutationDriver = mutationDriver;

  final IssueTransitionMutationDriver _mutationDriver;

  @override
  Future<IssueMutationResult<TrackStateIssue>> transitionIssue({
    required String repositoryPath,
    required String issueKey,
    required String status,
  }) async {
    return _mutationDriver.transitionIssue(
      repositoryPath: repositoryPath,
      issueKey: issueKey,
      status: status,
    );
  }
}
