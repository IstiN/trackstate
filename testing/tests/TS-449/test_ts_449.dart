import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts449_initial_shell_fixture.dart';

void main() {
  testWidgets(
    'TS-449 initial shell rendering stays interactive while hydration continues',
    (tester) async {
      final semantics = tester.ensureSemantics();
      Ts449InitialShellFixture? fixture;

      try {
        fixture = await tester.runAsync(Ts449InitialShellFixture.create);
        if (fixture == null) {
          throw StateError('TS-449 fixture creation did not complete.');
        }

        final TrackStateAppComponent app = defaultTestingDependencies
            .createTrackStateAppScreen(tester);
        await app.pump(fixture.repository);

        final failures = <String>[];
        final initialVisibleTexts = app.visibleTextsSnapshot();
        final initialSemantics = app.visibleSemanticsLabelsSnapshot();
        final initialExceptions = _drainFrameworkExceptions(tester);
        final connectGitHubVisible =
            await app.isSemanticsLabelVisible('Connect GitHub') ||
            await app.isTextVisible('Connect GitHub');
        final localGitVisible =
            await app.isSemanticsLabelVisible('Local Git') ||
            await app.isTextVisible('Local Git');

        if (fixture.repository.usesLocalPersistence ||
            !fixture.repository.supportsGitHubAuth) {
          failures.add(
            'Step 1 failed: the test did not exercise the hosted runtime requested by the ticket precondition. '
            'Observed repository flags: usesLocalPersistence=${fixture.repository.usesLocalPersistence}, '
            'supportsGitHubAuth=${fixture.repository.supportsGitHubAuth}.',
          );
        }

        if (!fixture.repository.initialSearchStarted ||
            fixture.repository.initialSearchCompleted) {
          failures.add(
            'Step 2 failed: the ticket requires observing the shell after loadSnapshot() completes but before the first searchIssuePage() hydration finishes. '
            'Observed search state: started=${fixture.repository.initialSearchStarted}, '
            'completed=${fixture.repository.initialSearchCompleted}, '
            'calls=${fixture.repository.searchPageCalls}.',
          );
        }

        if (find.byType(CircularProgressIndicator).evaluate().isNotEmpty) {
          failures.add(
            'Expected Result failed: the app still rendered a centered startup spinner instead of the app shell after the initial snapshot became available. '
            'Visible texts: ${_formatSnapshot(initialVisibleTexts)}. Visible semantics: ${_formatSnapshot(initialSemantics)}.',
          );
        }

        for (final requiredText in const [
          'TrackState.AI',
          'Git-native. Jira-compatible. Team-proven.',
          'Dashboard',
          'Board',
          'JQL Search',
          'Hierarchy',
          'Settings',
          'Synced with Git',
          'Create issue',
        ]) {
          if (!_snapshotContains(initialVisibleTexts, requiredText)) {
            failures.add(
              'Step 3 failed: the initial desktop shell did not render the visible "$requiredText" text while hydration was still in progress. '
              'Visible texts: ${_formatSnapshot(initialVisibleTexts)}.',
            );
          }
        }

        if (!connectGitHubVisible || localGitVisible) {
          failures.add(
            'Step 3 failed: the hosted shell did not expose the expected repository access state during hydration. '
            'Expected visible Connect GitHub=yes and Local Git=no, but observed Connect GitHub=${connectGitHubVisible ? 'yes' : 'no'} and Local Git=${localGitVisible ? 'yes' : 'no'}. '
            'Visible texts: ${_formatSnapshot(initialVisibleTexts)}. Visible semantics: ${_formatSnapshot(initialSemantics)}.',
          );
        }

        if (!_snapshotContains(initialVisibleTexts, 'Loading')) {
          failures.add(
            'Step 3 failed: the initial desktop shell did not render a visible loading indicator while hydration was still in progress. '
            'Visible texts: ${_formatSnapshot(initialVisibleTexts)}.',
          );
        }

        if (!_snapshotContains(initialSemantics, 'TrackState.AI navigation')) {
          failures.add(
            'Step 3 failed: the desktop sidebar navigation landmark was not exposed while the initial hydration was still loading.',
          );
        }

        if (!_snapshotContains(initialSemantics, 'Dashboard Loading')) {
          failures.add(
            'Step 2 failed: the Dashboard section did not expose the visible loading banner during the initial hydration window. '
            'Visible semantics: ${_formatSnapshot(initialSemantics)}.',
          );
        }

        if (initialExceptions.isNotEmpty) {
          failures.add(
            'Step 3 failed: rendering the initial shell surfaced framework exceptions.\n'
            'Exceptions:\n${initialExceptions.join('\n---\n')}',
          );
        }

        await _resizeViewport(tester, const Size(390, 844));

        final compactVisibleTexts = app.visibleTextsSnapshot();
        final compactExceptions = _drainFrameworkExceptions(tester);

        for (final requiredText in const [
          'TrackState.AI',
          'Dashboard',
          'Board',
          'JQL Search',
          'Hierarchy',
        ]) {
          if (!_snapshotContains(compactVisibleTexts, requiredText)) {
            failures.add(
              'Step 4 failed: after resizing to a compact viewport, the visible "$requiredText" shell text was missing during loading. '
              'Visible texts: ${_formatSnapshot(compactVisibleTexts)}.',
            );
          }
        }

        if (!_snapshotContains(compactVisibleTexts, 'Loading')) {
          failures.add(
            'Step 4 failed: after resizing to a compact viewport, no visible loading indicator remained in the shell while hydration was still pending. '
            'Visible texts: ${_formatSnapshot(compactVisibleTexts)}.',
          );
        }

        if (fixture.repository.initialSearchCompleted) {
          failures.add(
            'Step 4 failed: the delayed initial hydration finished before the compact-shell check completed, so the loading-state window was not preserved long enough for the responsive verification.',
          );
        }

        if (compactExceptions.isNotEmpty) {
          failures.add(
            'Step 4 failed: resizing the shell to a compact viewport surfaced framework exceptions.\n'
            'Exceptions:\n${compactExceptions.join('\n---\n')}',
          );
        }

        final boardNavigation = _exactNavigationButton('Board');
        if (boardNavigation.evaluate().isEmpty) {
          failures.add(
            'Step 5 failed: no interactive compact navigation control labeled "Board" was rendered while the main pane still showed loading placeholders. '
            'Visible texts: ${_formatSnapshot(compactVisibleTexts)}.',
          );
        } else {
          await tester.tap(boardNavigation.last, warnIfMissed: false);
          await tester.pump();
          await tester.pump(const Duration(milliseconds: 300));
        }

        final boardVisibleTexts = app.visibleTextsSnapshot();
        final boardSemantics = app.visibleSemanticsLabelsSnapshot();
        final boardExceptions = _drainFrameworkExceptions(tester);

        if (!boardVisibleTexts.contains('Board')) {
          failures.add(
            'Step 5 failed: tapping the compact navigation did not switch the user to the visible Board section while initial hydration was still pending. '
            'Visible texts: ${_formatSnapshot(boardVisibleTexts)}.',
          );
        }

        if (!_snapshotContains(boardSemantics, 'Board Loading')) {
          failures.add(
            'Step 5 failed: after switching sections during hydration, the Board section did not keep its loading banner visible. '
            'Visible semantics: ${_formatSnapshot(boardSemantics)}.',
          );
        }

        if (fixture.repository.initialSearchCompleted) {
          failures.add(
            'Step 5 failed: the initial hydration completed before navigation could be exercised, so the test could not confirm interaction during the loading state.',
          );
        }

        if (boardExceptions.isNotEmpty) {
          failures.add(
            'Step 5 failed: switching sections during hydration surfaced framework exceptions.\n'
            'Exceptions:\n${boardExceptions.join('\n---\n')}',
          );
        }

        await _pumpUntil(
          tester,
          condition: () => fixture!.repository.initialSearchCompleted,
          timeout: const Duration(seconds: 10),
          failureMessage: () {
            final hydrationError = fixture!.repository.lastSearchError;
            final errorDetails = hydrationError == null
                ? 'No repository error was captured.'
                : 'Repository error: $hydrationError.';
            return 'Expected Result failed: the delayed initial search never completed, so the test could not confirm that the selected section stays usable after hydration finishes. '
                'Observed search state: started=${fixture.repository.initialSearchStarted}, '
                'completed=${fixture.repository.initialSearchCompleted}, '
                'calls=${fixture.repository.searchPageCalls}. '
                '$errorDetails '
                'Visible texts: ${_formatSnapshot(app.visibleTextsSnapshot())}. '
                'Visible semantics: ${_formatSnapshot(app.visibleSemanticsLabelsSnapshot())}.';
          },
        );

        final hydratedBoardTexts = app.visibleTextsSnapshot();
        final hydratedBoardExceptions = _drainFrameworkExceptions(tester);

        final hydratedBoardSemantics = app.visibleSemanticsLabelsSnapshot();
        if (_snapshotContains(hydratedBoardSemantics, 'Board Loading')) {
          failures.add(
            'Expected Result failed: the Board section still exposed a loading banner after the delayed hydration window elapsed. '
            'Visible texts: ${_formatSnapshot(hydratedBoardTexts)}.',
          );
        }

        if (!hydratedBoardTexts.contains(
          Ts449InitialShellFixture.hydratedIssueSummary,
        )) {
          failures.add(
            'Expected Result failed: once hydration finished, the selected Board section did not continue rendering the visible issue content. '
            'Visible texts: ${_formatSnapshot(hydratedBoardTexts)}.',
          );
        }

        if (hydratedBoardExceptions.isNotEmpty) {
          failures.add(
            'Expected Result failed: completing the delayed hydration surfaced framework exceptions.\n'
            'Exceptions:\n${hydratedBoardExceptions.join('\n---\n')}',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Finder _exactNavigationButton(String label) => find.byWidgetPredicate(
  (widget) =>
      widget is Semantics &&
      widget.properties.button == true &&
      widget.properties.label == label,
  description: 'navigation button labeled $label',
);

Future<void> _resizeViewport(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  required Duration timeout,
  required String Function() failureMessage,
  Duration step = const Duration(milliseconds: 100),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      await tester.pump();
      return;
    }
    await tester.pump(step);
  }
  throw TestFailure(failureMessage());
}

List<String> _drainFrameworkExceptions(WidgetTester tester) {
  final messages = <String>[];
  Object? exception;
  while ((exception = tester.takeException()) != null) {
    messages.add(exception.toString());
  }
  return messages;
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
