import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-286 presents move validation failures with visible text and screen-reader semantics',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const expectedIssueKey = 'TRACK-41';
      const expectedIssueSummary = 'Polish mobile board interactions';
      const expectedMessage =
          'Move failed: Validation failed: Cannot move an issue under one of its descendants.';

      try {
        await screen.pump(const _Ts286MoveValidationFailureRepository());
        await screen.openSection('Board');

        await screen.dragIssueToStatusColumn(
          key: expectedIssueKey,
          summary: expectedIssueSummary,
          sourceStatusLabel: 'To Do',
          statusLabel: 'In Progress',
        );

        await screen.expectMessageBannerContains(expectedMessage);

        final visibleTexts = screen.visibleTextsSnapshot();
        final visibleSemantics = screen.visibleSemanticsLabelsSnapshot();
        final visibleMessage = visibleTexts.any(
          (value) => value.trim() == expectedMessage,
        );
        final semanticsMessage = visibleSemantics.any(
          (value) => value.trim() == expectedMessage,
        );

        expect(
          visibleMessage,
          isTrue,
          reason:
              'Step 2 failed: the move validation failure was not rendered as '
              'visible user-facing text. Visible texts: '
              '${_formatSnapshot(visibleTexts)}. Visible semantics: '
              '${_formatSnapshot(visibleSemantics)}.',
        );
        expect(
          semanticsMessage,
          isTrue,
          reason:
              'Step 3 failed: the visible move validation failure did not expose '
              'the same exact semantics label for screen readers. Visible '
              'semantics: ${_formatSnapshot(visibleSemantics)}. Visible texts: '
              '${_formatSnapshot(visibleTexts)}.',
        );
        await screen.expectMessageBannerAnnouncedAsLiveRegion(expectedMessage);
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

class _Ts286MoveValidationFailureRepository implements TrackStateRepository {
  const _Ts286MoveValidationFailureRepository();

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
  }) => _delegate.uploadIssueAttachment(
    issue: issue,
    name: name,
    bytes: bytes,
  );
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }

  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
