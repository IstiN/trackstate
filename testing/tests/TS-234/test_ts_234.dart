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
    'TS-234 discards create-issue draft after cancelling the overlay',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;
      const draftSummary = 'Discarded Draft';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-234 fixture creation did not complete.');
        }

        await screen.pumpLocalGitApp(repositoryPath: fixture.repositoryPath);
        screen.expectLocalRuntimeChrome();
        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        final createControlLabel = await _resolveTopBarCreateControlLabel(screen);
        if (createControlLabel == null) {
          fail(
            'Step 1 failed: no visible top-bar "Create" entry point was rendered '
            'in Local Git mode. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final openedCreateFlow = await screen.tapTopBarControl(createControlLabel);
        if (!openedCreateFlow) {
          fail(
            'Step 1 failed: the visible top-bar "$createControlLabel" control '
            'could not be activated. Top bar texts: '
            '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. Visible '
            'texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final summaryFieldVisible = await screen.isTextFieldVisible('Summary');
        if (!summaryFieldVisible) {
          fail(
            'Step 1 failed: opening "$createControlLabel" did not render the '
            '"Summary" field for issue creation. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.enterLabeledTextField('Summary', text: draftSummary);
        final enteredSummary = await screen.readLabeledTextFieldValue('Summary');
        if ((enteredSummary ?? '').trim() != draftSummary) {
          fail(
            'Step 2 failed: entering "$draftSummary" into Summary did not persist '
            'in the visible form. Actual Summary value: '
            '"${enteredSummary ?? '<missing>'}". Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}.',
          );
        }

        final cancelled = await screen.tapVisibleControl('Cancel');
        if (!cancelled) {
          fail(
            'Step 3 failed: the create form was open, but no visible "Cancel" '
            'action was reachable. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        final summaryStillVisible = await screen.isTextFieldVisible('Summary');
        if (summaryStillVisible) {
          fail(
            'Step 4 failed: tapping "Cancel" did not close the creation form; '
            'the Summary field is still visible. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final reopenedCreateFlow = await screen.tapTopBarControl(createControlLabel);
        if (!reopenedCreateFlow) {
          fail(
            'Step 5 failed: after cancelling, the top-bar "$createControlLabel" '
            'control was no longer reachable to reopen issue creation. Top bar '
            'texts: ${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final summaryVisibleAfterReopen = await screen.isTextFieldVisible('Summary');
        if (!summaryVisibleAfterReopen) {
          fail(
            'Step 5 failed: reopening "$createControlLabel" did not render the '
            'Summary field. Visible texts: '
            '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }

        final reopenedSummary = await screen.readLabeledTextFieldValue('Summary');
        if ((reopenedSummary ?? '').trim().isNotEmpty) {
          fail(
            'Expected result failed: reopening create after "Cancel" should show '
            'an empty Summary field, but it retained "${reopenedSummary ?? '<missing>'}". '
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
            'semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
          );
        }
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

Future<String?> _resolveTopBarCreateControlLabel(
  TrackStateAppComponent screen,
) async {
  for (final label in const ['Create issue', 'Create']) {
    if (await screen.isTopBarSemanticsLabelVisible(label) ||
        await screen.isTopBarTextVisible(label)) {
      return label;
    }
  }
  return null;
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
