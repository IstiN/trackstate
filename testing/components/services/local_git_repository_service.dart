import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/local_git_repository_port.dart';
import '../../frameworks/flutter/trackstate_test_runtime.dart';

class LocalGitRepositoryService implements LocalGitRepositoryPort {
  LocalGitRepositoryService(this._tester);

  final WidgetTester _tester;
  final Map<String, Future<TrackStateRepository>> _repositoriesByPath =
      <String, Future<TrackStateRepository>>{};

  @override
  Future<TrackStateRepository> openRepository({
    required String repositoryPath,
    Duration initialAppLoadDelay = Duration.zero,
  }) {
    final cacheKey =
        '$repositoryPath::${initialAppLoadDelay.inMicroseconds.toString()}';
    return _repositoriesByPath.putIfAbsent(cacheKey, () async {
      final repository = await createLocalGitTestRepository(
        tester: _tester,
        repositoryPath: repositoryPath,
      );
      if (initialAppLoadDelay == Duration.zero) {
        return repository;
      }
      return _InitialLoadDelayedTrackStateRepository(
        repository,
        initialLoadDelay: initialAppLoadDelay,
      );
    });
  }
}

class _InitialLoadDelayedTrackStateRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  _InitialLoadDelayedTrackStateRepository(
    this._delegate, {
    required this.initialLoadDelay,
  });

  final TrackStateRepository _delegate;
  final Duration initialLoadDelay;
  bool _initialLoadDelayed = false;

  @override
  bool get supportsGitHubAuth => _delegate.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => _delegate.usesLocalPersistence;

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    if (!_initialLoadDelayed) {
      _initialLoadDelayed = true;
      await Future<void>.delayed(initialLoadDelay);
    }
    return _delegate.loadSnapshot();
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) => _delegate.searchIssuePage(
    jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) =>
      _delegate.searchIssues(jql);

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) =>
      _delegate.deleteIssue(issue);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) =>
      _delegate.archiveIssue(issue);

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
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      _delegate.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      _delegate.loadIssueHistory(issue);

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) => _delegate.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);

  @override
  Future<TrackerSnapshot> saveProjectSettings(ProjectSettingsCatalog settings) {
    if (_delegate case final ProjectSettingsRepository settingsRepository) {
      return settingsRepository.saveProjectSettings(settings);
    }
    throw StateError(
      'Delayed repository does not support project settings admin.',
    );
  }
}
