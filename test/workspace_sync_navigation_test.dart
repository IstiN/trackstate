import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('sync pill opens settings and shows workspace sync diagnostics', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: TrackStateApp(repository: DemoTrackStateRepository()),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('workspace-sync-pill')).first);
    await tester.pumpAndSettle();

    expect(find.text('Workspace sync'), findsOneWidget);
    expect(find.text('Repository access'), findsOneWidget);
  });

  testWidgets(
    'hosted auth failures render Sync unavailable with a browser-readable sync pill label',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });
      final semantics = tester.ensureSemantics();

      try {
        await tester.pumpWidget(
          const MaterialApp(
            home: TrackStateApp(repository: _HostedAuthFailureRepository()),
          ),
        );

        await _pumpUntil(
          tester,
          condition: () =>
              find
                  .text('Sync unavailable', findRichText: true)
                  .evaluate()
                  .isNotEmpty,
        );

        final pill = find.byKey(const ValueKey('workspace-sync-pill')).first;
        expect(tester.getSemantics(pill).label, 'Sync unavailable');

        await tester.tap(pill, warnIfMissed: false);
        await tester.pumpAndSettle();

        expect(find.text('Workspace sync'), findsOneWidget);
        expect(
          find.textContaining('Bad credentials', findRichText: true),
          findsWidgets,
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  Duration timeout = const Duration(seconds: 5),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  expect(condition(), isTrue, reason: 'Timed out waiting for sync status.');
}

class _HostedAuthFailureRepository
    implements TrackStateRepository, WorkspaceSyncRepository {
  const _HostedAuthFailureRepository();

  static const TrackStateProviderException _authFailure =
      TrackStateProviderException(
        'GitHub API request failed for /repos/IstiN/trackstate-setup/branches/main (401): {"message":"Bad credentials"}',
      );

  final DemoTrackStateRepository _delegate = const DemoTrackStateRepository();

  @override
  bool get usesLocalPersistence => false;

  @override
  bool get supportsGitHubAuth => _delegate.supportsGitHubAuth;

  @override
  Future<RepositorySyncCheck> checkSync({
    RepositorySyncState? previousState,
  }) async {
    throw _authFailure;
  }

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
  }) => _delegate.uploadIssueAttachment(
    issue: issue,
    name: name,
    bytes: bytes,
  );

  @override
  Future<Uint8List> downloadAttachment(IssueAttachment attachment) =>
      _delegate.downloadAttachment(attachment);

  @override
  Future<List<IssueHistoryEntry>> loadIssueHistory(TrackStateIssue issue) =>
      _delegate.loadIssueHistory(issue);
}
