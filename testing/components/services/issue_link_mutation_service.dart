import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_link_mutation_driver.dart';
import '../../core/interfaces/issue_link_mutation_port.dart';

class IssueLinkMutationService implements IssueLinkMutationPort {
  IssueLinkMutationService({required IssueLinkMutationDriver mutationDriver})
    : _mutationDriver = mutationDriver;

  final IssueLinkMutationDriver _mutationDriver;

  @override
  Future<IssueMutationResult<TrackStateIssue>> createLink({
    required String repositoryPath,
    required String issueKey,
    required String targetKey,
    required String type,
  }) async {
    return _mutationDriver.createLink(
      repositoryPath: repositoryPath,
      issueKey: issueKey,
      targetKey: targetKey,
      type: type,
    );
  }
}
