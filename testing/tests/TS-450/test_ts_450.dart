import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts450_dashboard_bootstrap_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-450 dashboard bootstrap state keeps summary content visible with loading placeholders for unresolved fields',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final fixture = await Ts450DashboardBootstrapFixture.create();

      try {
        await screen.pump(fixture.repository);

        await _waitForCondition(
          tester,
          () async =>
              await screen.isSemanticsLabelVisible('Dashboard Loading...'),
          failureMessage:
              'Timed out waiting for the Dashboard bootstrap loading banner to appear.',
        );

        final failures = <String>[];
        final visibleTexts = screen.visibleTextsSnapshot();

        if (!fixture.sawRead(
          Ts450DashboardBootstrapFixture.bootstrapIndexPath,
        )) {
          failures.add(
            'Precondition failed: the hosted bootstrap snapshot did not read ${Ts450DashboardBootstrapFixture.bootstrapIndexPath}. '
            'Observed text-file reads: ${_formatSnapshot(fixture.textFileReads)}.',
          );
        }
        if (fixture.sawIssueMarkdownRead) {
          failures.add(
            'Precondition failed: issue markdown files were read before the dashboard bootstrap state was verified, so detail hydration was no longer pending. '
            'Observed text-file reads: ${_formatSnapshot(fixture.textFileReads)}.',
          );
        }
        if (fixture.searchRequestCount < 1) {
          failures.add(
            'Precondition failed: the initial dashboard load did not request the first hosted search page, so the hybrid bootstrap phase was never entered.',
          );
        }

        for (final requiredText in const [
          'Dashboard',
          'Open Issues',
          'Issues in Progress',
          'Completed',
          'Team Velocity',
          'Active Epics',
          'Recent Activity',
          '3',
          '2',
          '1',
          'TRACK-450E · Dashboard bootstrap epic summary',
          'TRACK-450-1 · Summary count sourced from issues index',
          'TRACK-450-2 · Loading placeholders keep unresolved fields readable',
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Step 2 failed: the dashboard bootstrap view did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        for (final semanticsLabel in const [
          'Dashboard Loading...',
          'Open Issues 3',
          'Issues in Progress 2',
          'Completed 1',
          'Team Velocity loading',
          'TRACK-450E Dashboard bootstrap epic summary 65 percent',
        ]) {
          if (!_normalizedSnapshot(
            screen.visibleSemanticsLabelsSnapshot(),
          ).contains(semanticsLabel)) {
            failures.add(
              'Step 3 failed: the dashboard bootstrap state did not expose the "$semanticsLabel" user-facing semantics label. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
            );
          }
        }

        fixture.releaseSearchResults();

        await _waitForCondition(
          tester,
          () async =>
              !await screen.isSemanticsLabelVisible('Dashboard Loading...') &&
              await screen.isTextVisible('42'),
          failureMessage:
              'Timed out waiting for the dashboard bootstrap placeholders to resolve after the initial search completed.',
        );

        if (await screen.isSemanticsLabelVisible('Dashboard Loading...')) {
          failures.add(
            'Step 4 failed: the dashboard still exposed the "Dashboard Loading..." bootstrap banner after the initial search completed.',
          );
        }
        if (await screen.isSemanticsLabelVisible('Team Velocity loading')) {
          failures.add(
            'Step 4 failed: unresolved dashboard fields did not transition out of their loading placeholder state after the initial search completed.',
          );
        }
        if (!await screen.isTextVisible('42')) {
          failures.add(
            'Step 4 failed: the Team Velocity card never exposed a visible resolved value after the bootstrap loading placeholders cleared. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }
        final resolvedSemantics = _normalizedSnapshot(
          screen.visibleSemanticsLabelsSnapshot(),
        );
        if (!resolvedSemantics.contains('Open Issues 3') ||
            !resolvedSemantics.contains('Issues in Progress 2') ||
            !resolvedSemantics.contains('Completed 1')) {
          failures.add(
            'Step 4 failed: metric counts sourced from the bootstrap index were not preserved after the loading placeholders resolved. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        fixture.releaseSearchResults();
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<void> _waitForCondition(
  WidgetTester tester,
  Future<bool> Function() condition, {
  required String failureMessage,
  Duration timeout = const Duration(seconds: 5),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(step);
    if (await condition()) {
      return;
    }
  }
  fail(failureMessage);
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = _normalizedSnapshot(values);
  if (snapshot.isEmpty) {
    return '<none>';
  }
  if (snapshot.length <= limit) {
    return snapshot.join(' | ');
  }
  return snapshot.take(limit).join(' | ');
}

List<String> _normalizedSnapshot(List<String> values) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
  }
  return snapshot;
}
