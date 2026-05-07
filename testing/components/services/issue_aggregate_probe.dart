import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_aggregate_loader.dart';

class IssueAggregateProbe implements IssueAggregateLoader {
  const IssueAggregateProbe(this._repository);

  final TrackStateRepository _repository;

  @override
  Future<TrackStateIssue> loadIssue(String issueKey) async {
    final snapshot = await _repository.loadSnapshot();
    try {
      return snapshot.issues.firstWhere((issue) => issue.key == issueKey);
    } on StateError {
      throw StateError(
        'Issue aggregate for $issueKey was not returned by loadSnapshot().',
      );
    }
  }
}
