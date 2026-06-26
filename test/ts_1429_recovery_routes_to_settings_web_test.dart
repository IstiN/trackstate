@TestOn('browser')
library;

import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/jql_search_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-444 recovery entry point routes to Settings with recovery callout',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 900);
      tester.view.devicePixelRatio = 1;

      try {
        final snapshot = await const DemoTrackStateRepository().loadSnapshot();
        final repository = _RecoveryRoutingRepository(
          snapshot: _withStartupRecovery(snapshot),
        );

        await tester.pumpWidget(TrackStateApp(repository: repository));
        await tester.pumpAndSettle();

        expect(
          find.text('Project Settings'),
          findsOneWidget,
          reason: 'The app should be routed to the Settings section.',
        );
        expect(
          find.text('GitHub startup limit reached'),
          findsOneWidget,
          reason:
              'The recovery callout title should appear exactly once; hidden '
              'web semantics copies must not create duplicate Text widgets.',
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Retry'),
          findsOneWidget,
          reason: 'The recovery callout should expose a single Retry action.',
        );
      } finally {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pumpAndSettle();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
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

class _RecoveryRoutingRepository implements TrackStateRepository {
  _RecoveryRoutingRepository({required TrackerSnapshot snapshot})
    : _snapshot = snapshot;

  final TrackerSnapshot _snapshot;
  final JqlSearchService _searchService = const JqlSearchService();

  @override
  bool get supportsGitHubAuth => true;

  @override
  bool get usesLocalPersistence => false;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'demo-user', displayName: 'Demo User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<TrackStateIssueSearchPage> searchIssuePage(
    String jql, {
    int startAt = 0,
    int maxResults = 50,
    String? continuationToken,
  }) async {
    return _searchService.search(
      issues: _snapshot.issues,
      project: _snapshot.project,
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
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async =>
      throw UnimplementedError();

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue;

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async =>
      issue;

  @override
  Future<TrackStateIssue> addIssueComment(
    TrackStateIssue issue,
    String body,
  ) async =>
      issue;

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) async =>
      Uint8List(0);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(
    TrackStateIssue issue,
  ) async =>
      const <IssueHistoryEntry>[];

  @override
  Future<TrackStateIssue> uploadIssueAttachment({
    required TrackStateIssue issue,
    required String name,
    required Uint8List bytes,
    String? sourceName,
  }) async =>
      issue;
}
