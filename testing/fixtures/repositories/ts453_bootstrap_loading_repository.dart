import 'dart:async';
import 'dart:typed_data';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

abstract interface class CancellableLoadingStateRepository
    implements TrackStateRepository {
  void cancelPendingLoadingWork();
}

class Ts453BootstrapLoadingRepository
    implements CancellableLoadingStateRepository {
  Ts453BootstrapLoadingRepository();

  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const JqlSearchService _searchService = JqlSearchService();

  Timer? _pendingSearchTimer;
  Completer<void>? _pendingSearchDelay;

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<TrackerSnapshot> loadSnapshot() async {
    final snapshot = await _delegate.loadSnapshot();
    return TrackerSnapshot(
      project: snapshot.project,
      issues: snapshot.issues,
      repositoryIndex: snapshot.repositoryIndex,
      loadWarnings: snapshot.loadWarnings,
      readiness: const TrackerBootstrapReadiness(
        domainStates: {
          TrackerDataDomain.projectMeta: TrackerLoadState.ready,
          TrackerDataDomain.issueSummaries: TrackerLoadState.ready,
          TrackerDataDomain.repositoryIndex: TrackerLoadState.ready,
          TrackerDataDomain.issueDetails: TrackerLoadState.partial,
        },
        sectionStates: {
          TrackerSectionKey.dashboard: TrackerLoadState.ready,
          TrackerSectionKey.board: TrackerLoadState.ready,
          TrackerSectionKey.search: TrackerLoadState.partial,
          TrackerSectionKey.hierarchy: TrackerLoadState.ready,
          TrackerSectionKey.settings: TrackerLoadState.ready,
        },
      ),
      startupRecovery: snapshot.startupRecovery,
    );
  }

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    final snapshot = await loadSnapshot();
    _pendingSearchTimer?.cancel();
    if (_pendingSearchDelay case final delay?) {
      if (!delay.isCompleted) {
        delay.complete();
      }
      _pendingSearchDelay = null;
    }

    final searchDelay = Completer<void>();
    _pendingSearchDelay = searchDelay;
    _pendingSearchTimer = Timer(const Duration(seconds: 8), () {
      _pendingSearchTimer = null;
      if (!searchDelay.isCompleted) {
        searchDelay.complete();
      }
      if (identical(_pendingSearchDelay, searchDelay)) {
        _pendingSearchDelay = null;
      }
    });
    await searchDelay.future;
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
      (await searchIssuePage(jql, maxResults: 2147483647)).issues;

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
    String? sourceName,
  }) => _delegate.uploadIssueAttachment(
    issue: issue,
    name: name,
    bytes: bytes,
    sourceName: sourceName,
  );

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      _delegate.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      _delegate.loadIssueHistory(issue);

  @override
  void cancelPendingLoadingWork() {
    _pendingSearchTimer?.cancel();
    _pendingSearchTimer = null;
    if (_pendingSearchDelay case final delay?) {
      if (!delay.isCompleted) {
        delay.complete();
      }
      _pendingSearchDelay = null;
    }
  }
}
