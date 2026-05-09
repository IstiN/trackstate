import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-182 keeps the Create issue overlay active with preserved data across tracker navigation',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      const preservedSummary = 'Refactor Persistence Verification';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-182 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        await screen.expectTextVisible(
          'Git-native. Jira-compatible. Team-proven.',
        );

        await _expectTopBarControlVisible(
          screen,
          label: 'Create issue',
          failingStep: 2,
          context: 'after navigating to Dashboard in Local Git mode',
        );

        final openedCreateFlow = await screen.tapTopBarControl('Create issue');
        expect(
          openedCreateFlow,
          isTrue,
          reason:
              'Step 2 failed: the visible top-bar "Create issue" control in '
              'Dashboard was not reachable. Top bar texts: '
              '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Dashboard',
        );
        await screen.enterLabeledTextField('Summary', text: preservedSummary);
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          preservedSummary,
          reason:
              'Step 3 failed: after typing the Summary field in Dashboard, the '
              'visible value did not match the entered text "$preservedSummary". '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.openSection('Board');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));
        final boardBackgroundVisible = await screen.isTextVisible(
          'Drag-ready workflow columns backed by Git files',
        );
        final summaryStillVisibleAfterNavigation = await screen
            .isTextFieldVisible('Summary');
        final summaryValueAfterNavigation = summaryStillVisibleAfterNavigation
            ? await screen.readLabeledTextFieldValue('Summary')
            : '<overlay closed>';
        expect(
          boardBackgroundVisible,
          isTrue,
          reason:
              'Step 4 failed: clicking the sidebar "Board" entry while the '
              'Create issue overlay was open did not switch the background view '
              'to Board. Expected the user-facing Board hint '
              '"Drag-ready workflow columns backed by Git files" to appear. '
              'Summary visible after navigation attempt='
              '$summaryStillVisibleAfterNavigation, Summary value after '
              'navigation attempt="$summaryValueAfterNavigation". Top bar '
              'texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        expect(
          await screen.isTextFieldVisible('Summary'),
          isTrue,
          reason:
              'Step 5 failed: navigating to Board closed the Create issue '
              'overlay instead of keeping it active. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          preservedSummary,
          reason:
              'Step 5 failed: the Create issue overlay stayed visible in Board, '
              'but the Summary field lost the entered text "$preservedSummary". '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        final descriptionVisible = await screen.isTextFieldVisible(
          'Description',
        );
        final saveVisible =
            await screen.isSemanticsLabelVisible('Save') ||
            await screen.isTextVisible('Save');
        final cancelVisible =
            await screen.isSemanticsLabelVisible('Cancel') ||
            await screen.isTextVisible('Cancel');
        expect(
          descriptionVisible && saveVisible && cancelVisible,
          isTrue,
          reason:
              'Step 5 failed: Board navigation should leave the full Create '
              'issue overlay active, but one or more controls were missing. '
              'Expected Description=${descriptionVisible ? 'visible' : 'missing'}, '
              'Save=${saveVisible ? 'visible' : 'missing'}, '
              'Cancel=${cancelVisible ? 'visible' : 'missing'}. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        final cancelled = await screen.tapVisibleControl('Cancel');
        expect(
          cancelled,
          isTrue,
          reason:
              'Cleanup failed: the preserved Create issue overlay could not be '
              'dismissed with the visible Cancel action. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Cleanup failed: Cancel should close the Create issue overlay, but '
              'the Summary field stayed visible.',
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<void> _expectTopBarControlVisible(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
  required String context,
}) async {
  final topBarTexts = screen.topBarVisibleTextsSnapshot();
  if (topBarTexts.any((value) => value.trim() == label)) {
    return;
  }

  fail(
    'Step $failingStep failed: no visible "$label" control was rendered in the '
    'top bar $context. Top bar texts: ${_formatSnapshot(topBarTexts)}. Visible '
    'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
    'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
