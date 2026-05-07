import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

TrackStateRepository createTs41LiveAppRepository({
  required WidgetTester tester,
  required TrackStateRepository repository,
}) {
  return _Ts41LiveAppRepository(tester: tester, repository: repository);
}

class _Ts41LiveAppRepository implements TrackStateRepository {
  const _Ts41LiveAppRepository({
    required this.tester,
    required this.repository,
  });

  final WidgetTester tester;
  final TrackStateRepository repository;

  @override
  bool get supportsGitHubAuth => repository.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => repository.usesLocalPersistence;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) {
    return repository.connect(connection);
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() => repository.loadSnapshot();

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) {
    return repository.searchIssues(jql);
  }

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    final updated = await tester.runAsync(
      () => repository.updateIssueStatus(issue, status),
    );
    if (updated == null) {
      throw StateError('TS-41 live app status update did not complete.');
    }
    return updated;
  }
}
