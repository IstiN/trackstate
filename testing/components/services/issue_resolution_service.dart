import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/issue_resolution_repository.dart';

class IssueResolutionService {
  const IssueResolutionService(this._repository);

  final IssueResolutionRepository _repository;

  Future<IssueResolutionResult> resolveIssueByKey(String key) async {
    final snapshot = await _repository.loadSnapshot();
    final issue = snapshot.issues.where((entry) => entry.key == key).firstOrNull;
    if (issue == null) {
      throw StateError(
        'Issue $key was not found. Snapshot contains: '
        '${snapshot.issues.map((entry) => entry.key).join(', ')}',
      );
    }

    return IssueResolutionResult(project: snapshot.project, issue: issue);
  }
}

class IssueResolutionResult {
  const IssueResolutionResult({required this.project, required this.issue});

  final ProjectConfig project;
  final TrackStateIssue issue;
}
