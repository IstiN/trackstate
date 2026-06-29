import 'dart:typed_data';

import 'package:flutter/semantics.dart';
import 'package:flutter/widgets.dart' show Semantics;
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
    'TS-1140 mutation feedback exposes a liveRegion semantics widget',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const expectedIssueKey = 'TRACK-41';
      const expectedIssueSummary = 'Polish mobile board interactions';
      const expectedMessage =
          'Move failed: Validation failed: Cannot move an issue under one of its descendants.';

      try {
        await screen.pump(const _Ts1140MoveValidationFailureRepository());
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

        expect(
          visibleMessage,
          isTrue,
          reason:
              'Step 1 failed: the mutation feedback banner did not render the '
              'exact visible error message a user should see. Visible texts: '
              '${_formatSnapshot(visibleTexts)}. Visible semantics: '
              '${_formatSnapshot(visibleSemantics)}.',
        );

        final semanticsFinder = find.byWidgetPredicate(
          (widget) =>
              widget is Semantics &&
              widget.properties.label?.trim() == expectedMessage,
          description:
              'Semantics widget wrapping the mutation feedback message',
        );
        final semanticsWidgets = tester.widgetList<Semantics>(semanticsFinder);
        final liveRegionWidgets = semanticsWidgets
            .where((widget) => widget.properties.liveRegion == true)
            .toList(growable: false);

        expect(
          semanticsWidgets,
          isNotEmpty,
          reason:
              'Step 2 failed: no Semantics widget exposed the exact mutation '
              'feedback label "$expectedMessage". Visible semantics: '
              '${_formatSnapshot(visibleSemantics)}. Visible texts: '
              '${_formatSnapshot(visibleTexts)}.',
        );
        expect(
          liveRegionWidgets,
          isNotEmpty,
          reason:
              'Step 3 failed: the Semantics widget wrapping the mutation '
              'feedback message did not enable liveRegion. Matching widget '
              'count: ${semanticsWidgets.length}. Visible semantics: '
              '${_formatSnapshot(visibleSemantics)}.',
        );

        final liveRegionNode = find.semantics.byPredicate(
          (node) =>
              node.getSemanticsData().label.trim() == expectedMessage &&
              node.getSemanticsData().hasFlag(SemanticsFlag.isLiveRegion),
          describeMatch: (_) =>
              'live-region semantics node for the mutation feedback message',
        );

        expect(
          liveRegionNode.evaluate(),
          isNotEmpty,
          reason:
              'Human-style verification failed: the visible mutation feedback '
              'message was present, but the semantics tree did not expose it as '
              'a live-region announcement for screen readers. Visible '
              'semantics: ${_formatSnapshot(visibleSemantics)}. Visible texts: '
              '${_formatSnapshot(visibleTexts)}.',
        );
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

class _Ts1140MoveValidationFailureRepository implements TrackStateRepository {
  const _Ts1140MoveValidationFailureRepository();

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