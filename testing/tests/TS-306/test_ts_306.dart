import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import 'support/ts306_create_issue_failure_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'TS-306 surfaces create issue provider failures and preserves the draft',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      const summaryValue = 'TS-306 provider failure draft';
      const descriptionValue =
          'The create issue dialog should keep this description after a shared mutation failure.';
      const firstLabel = 'draft-preserved';
      const secondLabel = 'needs-retry';
      final fixture = await Ts306CreateIssueFailureFixture.create();

      try {
        await screen.pump(fixture.repository);

        final createIssueSection = await screen.openCreateIssueFlow();
        await screen.expectCreateIssueFormVisible(
          createIssueSection: createIssueSection,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Description',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );
        await _expectCreateFieldVisible(
          screen,
          label: 'Labels',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );
        await _expectVisibleControl(
          screen,
          label: 'Save',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );
        await _expectVisibleControl(
          screen,
          label: 'Cancel',
          createIssueSection: createIssueSection,
          failingStep: 1,
        );

        await screen.populateCreateIssueForm(
          summary: summaryValue,
          description: descriptionValue,
        );
        await screen.enterLabeledTextField(
          'Labels',
          text: '$firstLabel,$secondLabel,',
        );

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          summaryValue,
          reason:
              'Step 2 failed: the Summary field did not retain "$summaryValue" before Save.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          descriptionValue,
          reason:
              'Step 2 failed: the Description field did not retain the typed draft before Save.',
        );
        expect(
          await screen.isTextVisible(firstLabel),
          isTrue,
          reason:
              'Step 2 failed: the first Labels chip "$firstLabel" was not visible before Save. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(secondLabel),
          isTrue,
          reason:
              'Step 2 failed: the second Labels chip "$secondLabel" was not visible before Save. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        await screen.submitCreateIssue(createIssueSection: createIssueSection);
        await screen.waitWithoutInteraction(const Duration(milliseconds: 800));

        expect(
          fixture.mutationAttemptCount,
          1,
          reason:
              'Step 3 failed: the shared mutation request was expected to reach the provider exactly once.',
        );
        expect(
          await screen.isMessageBannerVisibleContaining('Save failed:'),
          isTrue,
          reason:
              'Step 4 failed: no visible save failure banner was shown after the provider-backed create request failed. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isMessageBannerVisibleContaining(
            Ts306CreateIssueFailureFixture.providerFailureMessage,
          ),
          isTrue,
          reason:
              'Step 4 failed: the visible save failure banner did not surface the typed provider-failure message. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );

        expect(
          await screen.isTextFieldVisible('Summary'),
          isTrue,
          reason:
              'Step 4 failed: the Create issue form closed after the failed save instead of staying open for correction.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          summaryValue,
          reason:
              'Step 4 failed: the Summary field lost the user draft after the provider failure.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          descriptionValue,
          reason:
              'Step 4 failed: the Description field lost the user draft after the provider failure.',
        );
        expect(
          await screen.isTextVisible(firstLabel),
          isTrue,
          reason:
              'Step 4 failed: the first Labels chip "$firstLabel" was not preserved after the provider failure. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
        expect(
          await screen.isTextVisible(secondLabel),
          isTrue,
          reason:
              'Step 4 failed: the second Labels chip "$secondLabel" was not preserved after the provider failure. '
              'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
              'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
        );
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );
}

Future<void> _expectCreateFieldVisible(
  TrackStateAppComponent screen, {
  required String label,
  required String createIssueSection,
  required int failingStep,
}) async {
  if (await screen.isTextFieldVisible(label)) {
    return;
  }
  fail(
    'Step $failingStep failed: opening Create issue from $createIssueSection did not render the visible "$label" field. '
    'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
    'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
  );
}

Future<void> _expectVisibleControl(
  TrackStateAppComponent screen, {
  required String label,
  required String createIssueSection,
  required int failingStep,
}) async {
  final isVisible =
      await screen.isSemanticsLabelVisible(label) ||
      await screen.isTextVisible(label);
  if (isVisible) {
    return;
  }
  fail(
    'Step $failingStep failed: opening Create issue from $createIssueSection did not render the visible "$label" action. '
    'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}. '
    'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}.',
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
