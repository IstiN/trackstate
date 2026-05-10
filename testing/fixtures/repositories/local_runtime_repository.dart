import 'dart:typed_data';

import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

class LocalRuntimeRepository implements TrackStateRepository {
  const LocalRuntimeRepository();

  static const _demoRepository = DemoTrackStateRepository();

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async =>
      _demoRepository.loadSnapshot();

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      _demoRepository.searchIssues(jql);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime fixture is read-only for issue archiving.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime fixture is read-only for issue deletion.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw UnimplementedError('Issue creation is not implemented.');
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> addIssueComment(TrackStateIssue issue, String body) async =>
      issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) async =>
      const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
  }) async => issue;
}
