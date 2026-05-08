import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

Future<TrackStateRepository> createLocalGitTestRepository({
  required WidgetTester tester,
  required String repositoryPath,
}) async {
  final repository = createTrackStateRepository(
    runtime: TrackStateRuntime.localGit,
    localRepositoryPath: repositoryPath,
  );
  final snapshot = await tester.runAsync(repository.loadSnapshot);
  if (snapshot == null) {
    throw StateError('Local Git snapshot loading did not complete.');
  }
  final user = await tester.runAsync(
    () => repository.connect(
      RepositoryConnection(
        repository: snapshot.project.repository,
        branch: snapshot.project.branch,
        token: '',
      ),
    ),
  );
  if (user == null) {
    throw StateError('Local Git user resolution did not complete.');
  }
  return _PreloadedLocalGitRepository(
    repository: repository,
    snapshot: snapshot,
    user: user,
  );
}

class _PreloadedLocalGitRepository implements TrackStateRepository {
  const _PreloadedLocalGitRepository({
    required this.repository,
    required this.snapshot,
    required this.user,
  });

  final TrackStateRepository repository;
  final TrackerSnapshot snapshot;
  final RepositoryUser user;

  @override
  bool get supportsGitHubAuth => repository.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => repository.usesLocalPersistence;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async => user;

  @override
  Future<TrackerSnapshot> loadSnapshot() async => snapshot;

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) {
    return repository.searchIssues(jql);
  }

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) {
    return repository.deleteIssue(issue);
  }

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) {
    return repository.updateIssueStatus(issue, status);
  }
}
