import 'dart:typed_data';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../../core/utils/local_trackstate_fixture.dart';

class Ts449InitialShellFixture {
  Ts449InitialShellFixture._({
    required this.localFixture,
    required this.repository,
  });

  static const Duration initialSearchDelay = Duration(seconds: 4);

  final LocalTrackStateFixture localFixture;
  final Ts449DelayedInitialSearchRepository repository;

  static Future<Ts449InitialShellFixture> create() async {
    final localFixture = await LocalTrackStateFixture.create();
    final repository = Ts449DelayedInitialSearchRepository(
      localFixture.repository,
      initialSearchDelay: initialSearchDelay,
    );
    return Ts449InitialShellFixture._(
      localFixture: localFixture,
      repository: repository,
    );
  }

  Future<void> dispose() => localFixture.dispose();
}

class Ts449DelayedInitialSearchRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  Ts449DelayedInitialSearchRepository(
    this._delegate, {
    required this.initialSearchDelay,
  });

  final TrackStateRepository _delegate;
  final Duration initialSearchDelay;

  int searchPageCalls = 0;
  bool initialSearchStarted = false;
  bool initialSearchCompleted = false;

  @override
  bool get supportsGitHubAuth => _delegate.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => _delegate.usesLocalPersistence;

  @override
  Future<TrackerSnapshot> loadSnapshot() => _delegate.loadSnapshot();

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    searchPageCalls += 1;
    if (!initialSearchStarted) {
      initialSearchStarted = true;
      await Future<void>.delayed(initialSearchDelay);
    }
    final page = await _delegate.searchIssuePage(
      jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
    initialSearchCompleted = true;
    return page;
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) =>
      _delegate.searchIssues(jql);

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      _delegate.archiveIssue(issue);

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      _delegate.deleteIssue(issue);

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) => _delegate.createIssue(
    summary: summary,
    description: description,
    customFields: customFields,
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) => _delegate.updateIssueDescription(issue, description);

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) => _delegate.updateIssueStatus(issue, status);

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) =>
      _delegate.addIssueComment(issue, body);

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) => _delegate.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      _delegate.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      _delegate.loadIssueHistory(issue);

  @override
  Future<TrackerSnapshot> saveProjectSettings(ProjectSettingsCatalog settings) {
    if (_delegate case final ProjectSettingsRepository settingsRepository) {
      return settingsRepository.saveProjectSettings(settings);
    }
    throw StateError(
      'TS-449 delayed search repository does not support project settings.',
    );
  }
}
