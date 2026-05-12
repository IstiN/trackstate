import 'dart:typed_data';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class Ts410EditableSettingsRepository
    implements TrackStateRepository, ProjectSettingsRepository {
  Ts410EditableSettingsRepository()
    : _snapshot = const DemoTrackStateRepository().loadSnapshot();

  Future<TrackerSnapshot> _snapshot;
  ProjectSettingsCatalog? savedSettings;

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() => _snapshot;

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async => const DemoTrackStateRepository().searchIssuePage(
    jql,
    startAt: startAt,
    maxResults: maxResults,
    continuationToken: continuationToken,
  );

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      const DemoTrackStateRepository().searchIssues(jql);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Not implemented in test repository.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Not implemented in test repository.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async => throw const TrackStateRepositoryException(
    'Not implemented in test repository.',
  );

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async => issue;

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue;

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async => issue;

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async => const <IssueHistoryEntry>[];

  @override
  Future<TrackerSnapshot> saveProjectSettings(
    ProjectSettingsCatalog settings,
  ) async {
    savedSettings = settings;
    final current = await _snapshot;
    final updated = TrackerSnapshot(
      project: ProjectConfig(
        key: current.project.key,
        name: current.project.name,
        repository: current.project.repository,
        branch: current.project.branch,
        defaultLocale: current.project.defaultLocale,
        issueTypeDefinitions: settings.issueTypeDefinitions,
        statusDefinitions: settings.statusDefinitions,
        fieldDefinitions: settings.fieldDefinitions,
        workflowDefinitions: settings.workflowDefinitions,
        priorityDefinitions: current.project.priorityDefinitions,
        versionDefinitions: current.project.versionDefinitions,
        componentDefinitions: current.project.componentDefinitions,
        resolutionDefinitions: current.project.resolutionDefinitions,
      ),
      issues: current.issues,
      repositoryIndex: current.repositoryIndex,
      loadWarnings: current.loadWarnings,
    );
    _snapshot = Future<TrackerSnapshot>.value(updated);
    return updated;
  }
}
