import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/models/issue_key_resolution_observation.dart';

class IssueKeyResolutionService {
  const IssueKeyResolutionService({required this.repository});

  final TrackStateRepository repository;

  Future<IssueKeyResolutionObservation> resolveIssueByKey(String key) async {
    final snapshot = await repository.loadSnapshot();
    final issue = _findIssue(snapshot.issues, key);
    final searchResults = await repository.searchIssues(key);
    final indexEntry = snapshot.repositoryIndex.entryForKey(key);

    return IssueKeyResolutionObservation(
      key: issue.key,
      summary: issue.summary,
      indexPath: indexEntry?.path,
      storagePath: issue.storagePath,
      parentKey: issue.parentKey,
      parentPath: issue.parentPath,
      searchResultKeys: searchResults.map((entry) => entry.key).toList(),
      acceptanceCriteria: issue.acceptanceCriteria,
    );
  }

  TrackStateIssue _findIssue(List<TrackStateIssue> issues, String key) {
    for (final issue in issues) {
      if (issue.key == key) {
        return issue;
      }
    }
    throw StateError('Issue $key was not loaded from the repository snapshot.');
  }
}
