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
  return preloadLocalGitTestRepository(tester: tester, repository: repository);
}

Future<TrackStateRepository> preloadLocalGitTestRepository({
  required WidgetTester tester,
  required TrackStateRepository repository,
}) async {
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
  _PreloadedLocalGitRepository({
    required this.repository,
    required this.snapshot,
    required this.user,
  });

  final TrackStateRepository repository;
  final TrackerSnapshot snapshot;
  final RepositoryUser user;
  bool _servedInitialSnapshot = false;

  @override
  bool get supportsGitHubAuth => repository.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => repository.usesLocalPersistence;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async => user;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    if (!_servedInitialSnapshot) {
      _servedInitialSnapshot = true;
      return snapshot;
    }
    return repository.loadSnapshot();
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) =>
      repository.searchIssues(jql);

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) => repository.createIssue(
    summary: summary,
    description: description,
    customFields: customFields,
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => repository.updateIssueDescription(issue, description);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      repository.archiveIssue(issue);

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      repository.deleteIssue(issue);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) => repository.updateIssueStatus(issue, status);
}
