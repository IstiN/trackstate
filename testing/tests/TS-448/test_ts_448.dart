import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts448_mandatory_bootstrap_rate_limit_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-448 mandatory bootstrap rate limits keep the shell visible and non-Settings navigation disabled until retry succeeds',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final failures = <String>[];

      try {
        for (final artifact in Ts448MandatoryBootstrapArtifact.values) {
          final fixture = await Ts448MandatoryBootstrapRateLimitFixture.create(
            artifact: artifact,
          );

          await app.pump(fixture.repository);

          final scenario = fixture.artifactLabel;
          final visibleTexts = app.visibleTextsSnapshot();
          final visibleSemantics = app.visibleSemanticsLabelsSnapshot();

          if (fixture.requestCount(fixture.failingRequestPath) != 1) {
            failures.add(
              'Precondition failed for $scenario: the fixture did not trigger exactly one first-fetch GitHub rate-limit response for ${fixture.failingContentPath}. '
              'Observed requests: ${_formatSnapshot(fixture.requestedPaths)}.',
            );
          }

          for (final requiredText in const [
            'TrackState.AI',
            'Project Settings',
            'Dashboard',
            'Board',
            'JQL Search',
            'Hierarchy',
            'Settings',
            'GitHub startup limit reached',
            'Retry later or connect GitHub for a higher limit',
            'Retry',
          ]) {
            if (!_snapshotContains(visibleTexts, requiredText) &&
                !_snapshotContains(visibleSemantics, requiredText)) {
              failures.add(
                'Step 2 failed for $scenario: the shell-first recovery state did not keep the visible "$requiredText" content on screen after ${fixture.failingContentPath} hit the GitHub rate limit. '
                'Visible texts: ${_formatSnapshot(visibleTexts)}. '
                'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
              );
            }
          }

          if (_navigationFinder('Dashboard').evaluate().isEmpty ||
              _navigationFinder('Board').evaluate().isEmpty ||
              !_snapshotContains(
                visibleSemantics,
                'TrackState.AI navigation',
              )) {
            failures.add(
              'Step 2 failed for $scenario: the navigation chrome was not rendered in the recovery shell after ${fixture.failingContentPath} failed. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}. '
              'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
            );
          } else {
            await _assertNavigationDisabled(
              tester,
              app,
              failures: failures,
              scenario: scenario,
              label: 'Dashboard',
              disallowedTexts: const ['Open Issues', 'Team Velocity'],
            );
            await _assertNavigationDisabled(
              tester,
              app,
              failures: failures,
              scenario: scenario,
              label: 'Board',
              disallowedTexts: const ['Kanban by workflow', 'To Do'],
            );
          }

          final retryTapped = await app.tapVisibleControl('Retry');
          if (!retryTapped) {
            failures.add(
              'Step 4 failed for $scenario: the recovery container did not expose a tappable Retry action. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
            );
            continue;
          }

          await _waitForCondition(
            tester,
            condition: () async =>
                !await app.isTextVisible('GitHub startup limit reached') &&
                !_snapshotContains(
                  app.visibleSemanticsLabelsSnapshot(),
                  'GitHub startup limit reached',
                ),
            failureMessage:
                'Step 4 failed for $scenario: Retry did not clear the recovery container after ${fixture.failingContentPath} succeeded on the next load. '
                'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
                'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
          );

          if (!await app.tapVisibleControl('Dashboard')) {
            failures.add(
              'Expected result failed for $scenario: Dashboard was not tappable after Retry completed. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          } else if (!await app.isTextVisible('Open Issues') ||
              !await app.isTextVisible('Team Velocity')) {
            failures.add(
              'Expected result failed for $scenario: after Retry succeeded, Dashboard did not expose the expected user-visible summary content. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          }

          if (!await app.tapVisibleControl('Board')) {
            failures.add(
              'Expected result failed for $scenario: Board was not tappable after Retry completed. '
              'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
            );
          }
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        app.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Finder _navigationFinder(String label) => find.byWidgetPredicate(
  (widget) =>
      widget is Semantics &&
      widget.properties.button == true &&
      widget.properties.label == label,
  description: 'navigation control labeled $label',
);

Future<void> _assertNavigationDisabled(
  WidgetTester tester,
  TrackStateAppComponent app, {
  required List<String> failures,
  required String scenario,
  required String label,
  required List<String> disallowedTexts,
}) async {
  final target = _navigationFinder(label);
  if (target.evaluate().isEmpty) {
    failures.add(
      'Step 3 failed for $scenario: no visible navigation control labeled "$label" was rendered in the recovery shell.',
    );
    return;
  }

  final semanticsData = tester.getSemantics(target.last).getSemanticsData();
  final hasTapAction = semanticsData.hasAction(SemanticsAction.tap);
  final isEnabled = semanticsData.hasFlag(SemanticsFlag.isEnabled);

  if (hasTapAction || isEnabled) {
    failures.add(
      'Step 3 failed for $scenario: the "$label" navigation control remained enabled during mandatory bootstrap recovery. '
      'Semantics label="${semanticsData.label}", hasTapAction=$hasTapAction, isEnabled=$isEnabled.',
    );
  }

  await tester.tap(target.last, warnIfMissed: false);
  await tester.pumpAndSettle();

  if (!_snapshotContains(app.visibleTextsSnapshot(), 'Project Settings')) {
    failures.add(
      'Step 3 failed for $scenario: tapping "$label" navigated away from Settings while recovery was active. '
      'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}.',
    );
  }

  for (final disallowedText in disallowedTexts) {
    if (_snapshotContains(app.visibleTextsSnapshot(), disallowedText) ||
        _snapshotContains(
          app.visibleSemanticsLabelsSnapshot(),
          disallowedText,
        )) {
      failures.add(
        'Step 3 failed for $scenario: tapping "$label" surfaced "$disallowedText" while the recovery container was still active. '
        'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
        'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.',
      );
    }
  }
}

Future<void> _waitForCondition(
  WidgetTester tester, {
  required Future<bool> Function() condition,
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

bool _snapshotContains(List<String> values, String expected) {
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed == expected ||
        trimmed.startsWith(expected) ||
        trimmed.contains(expected)) {
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
