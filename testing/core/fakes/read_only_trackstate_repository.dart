import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class ReadOnlyTrackStateRepository implements TrackStateRepository {
  const ReadOnlyTrackStateRepository();

  static const DemoTrackStateRepository _demoRepository =
      DemoTrackStateRepository();

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _demoRepository.connect(connection);

  @override
  Future<TrackerSnapshot> loadSnapshot() => _demoRepository.loadSnapshot();

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) =>
      _demoRepository.searchIssues(jql);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    throw const TrackStateRepositoryException(
      'Connect a repository session with write access first.',
    );
  }
}
