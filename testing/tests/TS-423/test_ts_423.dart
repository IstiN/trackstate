import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../components/screens/readiness_state_accessibility_robot.dart';
import '../../components/screens/readiness_state_accessibility_screen.dart';
import '../../core/interfaces/readiness_state_accessibility_screen.dart';
import '../../core/models/loading_banner_theme_observation.dart';
import 'support/ts423_readiness_accessibility_fixture.dart';

void main() {
  testWidgets(
    'TS-423 readiness state accessibility keeps loading and partial-state feedback semantic and readable',
    (tester) async {
      final semantics = tester.ensureSemantics();
      Ts423ReadinessAccessibilityFixture? fixture;
      ReadinessStateAccessibilityScreenHandle? screen;

      try {
        fixture = await tester.runAsync(
          Ts423ReadinessAccessibilityFixture.create,
        );
        if (fixture == null) {
          throw StateError('TS-423 fixture creation did not complete.');
        }

        screen = ReadinessStateAccessibilityScreen(
          app: defaultTestingDependencies.createTrackStateAppScreen(tester),
          robot: ReadinessStateAccessibilityRobot(tester),
          repository: fixture.repository,
        );
        await screen.launch();
        await _pumpUntil(
          tester,
          condition: () => fixture!.repository.initialSearchStarted,
          timeout: const Duration(seconds: 2),
          failureMessage:
              'TS-423 could not enter the bootstrap loading window because the initial search never started.',
        );

        final failures = <String>[];
        final dashboardTexts = screen.visibleTexts();
        final dashboardSemantics = screen.visibleSemanticsLabels();

        if (fixture.repository.initialSearchCompleted) {
          failures.add(
            'Precondition failed: the delayed bootstrap loading window finished before the dashboard loading state could be inspected.',
          );
        }

        for (final requiredText in const ['Dashboard', 'Loading...']) {
          if (!_snapshotContains(dashboardTexts, requiredText)) {
            failures.add(
              'Step 2 failed: the dashboard loading state did not render the visible "$requiredText" text. '
              'Visible texts: ${_formatSnapshot(dashboardTexts)}.',
            );
          }
        }

        for (final requiredLabel in const [
          'Dashboard Loading...',
          'Team Velocity loading',
        ]) {
          if (!_snapshotContains(dashboardSemantics, requiredLabel)) {
            failures.add(
              'Step 3 failed: the dashboard loading state did not expose the semantics label "$requiredLabel". '
              'Visible semantics: ${_formatSnapshot(dashboardSemantics)}.',
            );
          }
        }

        _verifyLoadingBanner(
          failures,
          observation: screen.observeLoadingBanner('Dashboard Loading...'),
          context: 'dashboard loading banner',
        );

        await screen.openSection('Board');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final boardTexts = screen.visibleTexts();
        final boardSemantics = screen.visibleSemanticsLabels();
        for (final requiredText in const [
          'Board',
          'Loading...',
          Ts423ReadinessAccessibilityFixture.issueSummary,
        ]) {
          if (!_snapshotContains(boardTexts, requiredText)) {
            failures.add(
              'Step 2 failed: the board loading state did not keep the visible "$requiredText" text on screen. '
              'Visible texts: ${_formatSnapshot(boardTexts)}.',
            );
          }
        }
        if (!_snapshotContains(boardSemantics, 'Board Loading...')) {
          failures.add(
            'Step 3 failed: the board loading state did not expose the semantics label "Board Loading...". '
            'Visible semantics: ${_formatSnapshot(boardSemantics)}.',
          );
        }

        _verifyLoadingBanner(
          failures,
          observation: screen.observeLoadingBanner('Board Loading...'),
          context: 'board loading banner',
        );

        await screen.openIssue(
          Ts423ReadinessAccessibilityFixture.issueKey,
          Ts423ReadinessAccessibilityFixture.issueSummary,
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final issueDetailTexts = screen.visibleTextsWithinIssueDetail(
          Ts423ReadinessAccessibilityFixture.issueKey,
        );
        final issueDetailSemantics = screen.visibleSemanticsWithinIssueDetail(
          Ts423ReadinessAccessibilityFixture.issueKey,
        );

        for (final requiredText in const [
          Ts423ReadinessAccessibilityFixture.issueKey,
          Ts423ReadinessAccessibilityFixture.issueSummary,
          'Detail',
          'Loading...',
        ]) {
          if (!_snapshotContains(issueDetailTexts, requiredText)) {
            failures.add(
              'Step 4 failed: the partial issue detail panel did not keep the visible "$requiredText" text on screen. '
              'Visible issue-detail texts: ${_formatSnapshot(issueDetailTexts)}.',
            );
          }
        }

        if (_snapshotContains(
          issueDetailTexts,
          Ts423ReadinessAccessibilityFixture.issueDescription,
        )) {
          failures.add(
            'Step 4 failed: the issue detail body rendered the final description before the partial loading state could be observed. '
            'Visible issue-detail texts: ${_formatSnapshot(issueDetailTexts)}.',
          );
        }

        if (!_snapshotContains(issueDetailSemantics, 'Detail Loading...')) {
          failures.add(
            'Step 3 failed: the partial issue detail panel did not expose the semantics label "Detail Loading...". '
            'Visible issue-detail semantics: ${_formatSnapshot(issueDetailSemantics)}.',
          );
        }

        _verifyLoadingBanner(
          failures,
          observation: screen.observeIssueDetailLoadingBanner(
            Ts423ReadinessAccessibilityFixture.issueKey,
            semanticLabel: 'Detail Loading...',
          ),
          context: 'partial issue detail loading banner',
        );

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        screen?.dispose();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

void _verifyLoadingBanner(
  List<String> failures, {
  required LoadingBannerThemeObservation observation,
  required String context,
}) {
  if (!observation.usesExpectedTokens) {
    failures.add(
      'Expected Result failed: the $context did not use the TrackStateTheme loading tokens. '
      'Observed ${observation.describeTheme()}.',
    );
  }
  if (observation.contrastRatio < 4.5) {
    failures.add(
      'Step 5 failed: the $context contrast was ${observation.describeContrast()}, below the required WCAG AA 4.5:1 threshold.',
    );
  }
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  required Duration timeout,
  required String failureMessage,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  if (!condition()) {
    fail(failureMessage);
  }
}

bool _snapshotContains(List<String> snapshot, String expected) {
  for (final value in snapshot) {
    if (value.trim() == expected || value.contains(expected)) {
      return true;
    }
  }
  return false;
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
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
