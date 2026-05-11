import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/data/repositories/trackstate_runtime.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

Future<TrackStateRepository> createLocalGitTestRepository({
  required WidgetTester tester,
  required String repositoryPath,
}) async {
  final repository = await createLocalGitMutationRepository(
    tester: tester,
    repositoryPath: repositoryPath,
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

Future<ProviderBackedTrackStateRepository> createLocalGitMutationRepository({
  required WidgetTester tester,
  required String repositoryPath,
}) async {
  final repository = createTrackStateRepository(
    runtime: TrackStateRuntime.localGit,
    localRepositoryPath: repositoryPath,
  );
  if (repository case final ProviderBackedTrackStateRepository providerBacked) {
    await preloadProviderBackedLocalGitRepository(
      tester: tester,
      repository: providerBacked,
    );
    return providerBacked;
  }
  throw StateError(
    'Local Git test runtime requires a provider-backed repository.',
  );
}

Future<void> preloadProviderBackedLocalGitRepository({
  required WidgetTester tester,
  required ProviderBackedTrackStateRepository repository,
}) async {
  await preloadLocalGitTestRepository(tester: tester, repository: repository);
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

class _PreloadedLocalGitRepository
    implements TrackStateRepository, ProjectSettingsRepository {
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
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) => repository.searchIssuePage(
    jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

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

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) =>
      repository.addIssueComment(issue, body);

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      repository.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      repository.loadIssueHistory(issue);

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) =>
      repository.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);

  @override
  Future<TrackerSnapshot> saveProjectSettings(ProjectSettingsCatalog settings) {
    if (repository case final ProjectSettingsRepository settingsRepository) {
      return settingsRepository.saveProjectSettings(settings);
    }
    throw StateError(
      'Preloaded repository does not support project settings admin.',
    );
  }
}
