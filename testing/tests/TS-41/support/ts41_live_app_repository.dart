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
    return _runAsync(
      () => repository.connect(connection),
      step: 'repository connection',
    );
  }

  @override
  Future<TrackerSnapshot> loadSnapshot() {
    return _runAsync(repository.loadSnapshot, step: 'snapshot load');
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) {
    return _runAsync(() => repository.searchIssues(jql), step: 'issue search');
  }

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) {
    return _runAsync(
      () => repository.updateIssueStatus(issue, status),
      step: 'status update',
    );
  }

  Future<T> _runAsync<T>(
    Future<T> Function() operation, {
    required String step,
  }) async {
    final result = await tester.runAsync(operation);
    if (result == null) {
      throw StateError('TS-41 live app $step did not complete.');
    }
    return result;
  }
}
