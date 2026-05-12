import 'dart:typed_data';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts445SettingsRecoveryRepository implements TrackStateRepository {
  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const JqlSearchService _searchService = JqlSearchService();

  static Future<Ts445SettingsRecoveryRepository> create() async {
    final snapshot = await _delegate.loadSnapshot();
    return Ts445SettingsRecoveryRepository._(snapshot);
  }

  Ts445SettingsRecoveryRepository._(TrackerSnapshot snapshot)
    : _loadResults = <TrackerSnapshot>[
        _withStartupRecovery(snapshot),
        _withStartupRecovery(snapshot),
        _withStartupRecovery(snapshot),
      ];

  final List<TrackerSnapshot> _loadResults;
  TrackerSnapshot? _currentSnapshot;
  int loadCount = 0;

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final index = loadCount < _loadResults.length
        ? loadCount
        : _loadResults.length - 1;
    loadCount += 1;
    final snapshot = _loadResults[index];
    _currentSnapshot = snapshot;
    return snapshot;
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final snapshot = _currentSnapshot ?? await loadSnapshot();
    return _searchService.search(
      issues: snapshot.issues,
      project: snapshot.project,
      jql: jql,
      startAt: startAt,
      maxResults: maxResults,
      continuationToken: continuationToken,
    );
  }

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      (await searchIssuePage(jql, maxResults: 500)).issues;

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
}

TrackerSnapshot _withStartupRecovery(TrackerSnapshot snapshot) {
  return TrackerSnapshot(
    project: snapshot.project,
    issues: snapshot.issues,
    repositoryIndex: snapshot.repositoryIndex,
    loadWarnings: snapshot.loadWarnings,
    readiness: snapshot.readiness,
    startupRecovery: const TrackerStartupRecovery(
      kind: TrackerStartupRecoveryKind.githubRateLimit,
      failedPath:
          '/repos/trackstate/trackstate/contents/.trackstate/index/tombstones.json',
    ),
  );
}
