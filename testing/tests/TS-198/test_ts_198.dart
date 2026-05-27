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
    'TS-198 keeps a single Create issue overlay active when Create issue is triggered twice',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      const preservedSummary = 'Singleton Pattern Verification';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-198 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();

        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        await screen.expectTextVisible(
          'Git-native. Jira-compatible. Team-proven.',
        );

        final createIssueVisible =
            await screen.isTopBarSemanticsLabelVisible('Create issue') ||
            await screen.isTopBarTextVisible('Create issue');
        expect(
          createIssueVisible,
          isTrue,
          reason:
              'Step 2 failed: Dashboard did not expose a visible top-bar '
              '"Create issue" control. Top bar texts: '
              '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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

        final reopenedCreateFlow = await screen.tapTopBarControl(
          'Create issue',
        );
        expect(
          reopenedCreateFlow,
          isTrue,
          reason:
              'Step 4 failed: the top-bar "Create issue" control was no longer '
              'reachable while the create overlay was already open. Top bar '
              'texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final summaryFieldCount = await screen.countLabeledTextFields(
          'Summary',
        );
        expect(
          summaryFieldCount,
          1,
          reason:
              'Step 5 failed: clicking the top-bar "Create issue" control a '
              'second time should keep a single create overlay instance, but '
              'rendered $summaryFieldCount visible Summary field(s). Top bar '
              'texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        expect(
          await screen.isTextFieldVisible('Summary'),
          isTrue,
          reason:
              'Step 5 failed: the Create issue overlay was no longer visible '
              'after clicking the top-bar "Create issue" control a second time. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          preservedSummary,
          reason:
              'Step 5 failed: the Create issue overlay stayed visible after the '
              'second top-bar click, but the Summary field lost the entered text '
              '"$preservedSummary". Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
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
              'Step 5 failed: the repeated top-bar "Create issue" action should '
              'leave the full Create issue overlay active, but one or more '
              'controls were missing. Expected Description='
              '${descriptionVisible ? 'visible' : 'missing'}, Save='
              '${saveVisible ? 'visible' : 'missing'}, Cancel='
              '${cancelVisible ? 'visible' : 'missing'}. Visible texts: '
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
