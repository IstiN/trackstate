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
    'TS-199 clears the Create issue draft after the user closes the overlay',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      const typedSummary = 'Temporary Draft Data';

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('TS-199 fixture creation did not complete.');
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
          failingStep: 1,
          context: 'after navigating to Dashboard in Local Git mode',
        );

        final openedCreateFlow = await screen.tapTopBarControl('Create issue');
        expect(
          openedCreateFlow,
          isTrue,
          reason:
              'Step 1 failed: the visible top-bar "Create issue" control on '
              'Dashboard was not reachable. Top bar texts: '
              '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Dashboard',
        );
        await _expectVisibleControl(
          screen,
          label: 'Save',
          failingStep: 1,
          context: 'after opening Create issue from Dashboard',
        );
        await _expectVisibleControl(
          screen,
          label: 'Cancel',
          failingStep: 1,
          context: 'after opening Create issue from Dashboard',
        );
        expect(
          await screen.isTextFieldVisible('Description'),
          isTrue,
          reason:
              'Step 1 failed: opening Create issue from Dashboard did not '
              'render the visible Description field. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.enterLabeledTextField('Summary', text: typedSummary);
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          typedSummary,
          reason:
              'Step 2 failed: after typing the Summary field, the visible value '
              'did not match "$typedSummary". Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        final cancelled = await screen.tapVisibleControl('Cancel');
        expect(
          cancelled,
          isTrue,
          reason:
              'Step 3 failed: the visible "Cancel" action could not dismiss the '
              'Create issue overlay. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Step 3 failed: tapping "Cancel" should close the Create issue '
              'overlay, but the Summary field remained visible. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await _expectTopBarControlVisible(
          screen,
          label: 'Create issue',
          failingStep: 4,
          context: 'after cancelling the Create issue overlay on Dashboard',
        );

        final reopenedCreateFlow = await screen.tapTopBarControl(
          'Create issue',
        );
        expect(
          reopenedCreateFlow,
          isTrue,
          reason:
              'Step 4 failed: the visible top-bar "Create issue" control could '
              'not be activated after cancelling the previous overlay. Top bar texts: '
              '${_formatSnapshot(screen.topBarVisibleTextsSnapshot())}. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.expectCreateIssueFormVisible(
          createIssueSection: 'Dashboard',
        );
        await _expectVisibleControl(
          screen,
          label: 'Save',
          failingStep: 5,
          context: 'after reopening Create issue from Dashboard',
        );
        await _expectVisibleControl(
          screen,
          label: 'Cancel',
          failingStep: 5,
          context: 'after reopening Create issue from Dashboard',
        );
        expect(
          await screen.isTextFieldVisible('Description'),
          isTrue,
          reason:
              'Step 5 failed: reopening Create issue from Dashboard did not '
              'render the visible Description field. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          isEmpty,
          reason:
              'Step 5 failed: reopening the Create issue form after cancelling '
              'it should show an empty Summary field, but the user still saw '
              '"${await screen.readLabeledTextFieldValue('Summary') ?? '<missing>'}". '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        final finalCancel = await screen.tapVisibleControl('Cancel');
        expect(
          finalCancel,
          isTrue,
          reason:
              'Cleanup failed: the reopened Create issue overlay could not be '
              'dismissed with the visible Cancel action. Visible texts: '
              '${_formatSnapshot(screen.visibleTextsSnapshot())}. Visible '
              'semantics: '
              '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextFieldVisible('Summary'),
          isFalse,
          reason:
              'Cleanup failed: Cancel should close the reopened Create issue '
              'overlay, but the Summary field stayed visible.',
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

Future<void> _expectVisibleControl(
  TrackStateAppComponent screen, {
  required String label,
  required int failingStep,
  required String context,
}) async {
  final isVisible =
      await screen.isSemanticsLabelVisible(label) ||
      await screen.isTextVisible(label);
  if (isVisible) {
    return;
  }
  fail(
    'Step $failingStep failed: no visible "$label" control was rendered '
    '$context. Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
    'Visible semantics: '
    '${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
