import 'dart:typed_data';

import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/interfaces/trackstate_app_component.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'move validation failures are exposed as live-region semantics alerts',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      const expectedMessage =
          'Move failed: Validation failed: Cannot move an issue under one of its descendants.';

      try {
        await screen.pump(const _MoveValidationFailureRepository());
        await screen.openSection('Board');
        await screen.dragIssueToStatusColumn(
          key: 'TRACK-41',
          summary: 'Polish mobile board interactions',
          sourceStatusLabel: 'To Do',
          statusLabel: 'In Progress',
        );

        await screen.expectMessageBannerAnnouncedAsLiveRegion(expectedMessage);

        final liveRegionAlert = find.semantics.byPredicate(
          (node) =>
              node.getSemanticsData().label.trim() == expectedMessage &&
              node.getSemanticsData().hasFlag(SemanticsFlag.isLiveRegion), // ignore: deprecated_member_use
          describeMatch: (_) =>
              'live-region semantics node for the move validation failure banner',
        );
        expect(liveRegionAlert, findsWidgets);
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
  );
}

class _MoveValidationFailureRepository implements TrackStateRepository {
  const _MoveValidationFailureRepository();

  static const DemoTrackStateRepository _delegate = DemoTrackStateRepository();
  static const String _validationFailure =
      'Validation failed: Cannot move an issue under one of its descendants.';

  @override
  bool get supportsGitHubAuth => _delegate.supportsGitHubAuth;

  @override
  bool get usesLocalPersistence => _delegate.usesLocalPersistence;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) =>
      _delegate.connect(connection);

  @override
  Future<TrackerSnapshot> loadSnapshot() => _delegate.loadSnapshot();

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
  ) async {
    throw const TrackStateRepositoryException(_validationFailure);
  }

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
    String? sourceName,
  }) => _delegate.uploadIssueAttachment(issue: issue, name: name, bytes: bytes);
}