import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_edit_accessibility_screen.dart';
import '../../fixtures/issue_edit_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-402 Issue Edit Surface accessibility keeps focus order, semantics labels, validation feedback, and summary placeholder contrast aligned with AC6',
    (tester) async {
      final semantics = tester.ensureSemantics();
      IssueEditAccessibilityScreenHandle? screen;

      try {
        screen = await launchIssueEditAccessibilityFixture(tester);
        final failures = <String>[];

        final visibleTexts = screen.visibleTexts();
        for (final requiredText in const [
          'Edit issue',
          'Current status',
          'Status',
          'Summary',
          'Description',
          'Priority',
          'Assignee',
          'Labels',
          'Components',
          'Fix versions',
          'Epic',
          'Save',
          'Cancel',
        ]) {
          if (!screen.showsText(requiredText)) {
            failures.add(
              'Step 1 failed: opening the Issue Edit Surface did not render the visible "$requiredText" text. '
              'Visible edit-surface text: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        final semanticsLabels = screen.visibleSemanticsLabels();
        for (final requiredLabel in const [
          'Status',
          'Summary',
          'Description',
          'Priority',
          'Assignee',
          'Labels',
          'Components',
          'Fix versions',
          'Epic',
          'Save',
          'Cancel',
        ]) {
          if (!_containsLabel(semanticsLabels, requiredLabel)) {
            failures.add(
              'Step 3 failed: the Issue Edit Surface did not expose a non-empty semantics label for "$requiredLabel". '
              'Visible semantics labels: ${_formatSnapshot(semanticsLabels)}.',
            );
          }
        }

        final traversal = screen.semanticsTraversal();
        final traversalFailure = _orderedSubsequenceFailure(
          traversal,
          expectedOrder: const [
            'Status',
            'Summary',
            'Description',
            'Priority',
            'Assignee',
            'Labels',
            'Components',
            'Fix versions',
            'Epic',
            'Save',
            'Cancel',
          ],
        );
        if (traversalFailure != null) {
          failures.add(
            '$traversalFailure Observed screen-reader traversal: ${traversal.join(' -> ')}.',
          );
        }

        final forwardFocusOrder = await screen.collectForwardFocusOrder();
        final focusFailure = _orderedSubsequenceFailure(
          forwardFocusOrder,
          expectedOrder: const [
            'Status',
            'Summary',
            'Description',
            'Priority',
            'Assignee',
            'Labels',
            'Components',
            'Fix versions',
            'Epic',
            'Save',
            'Cancel',
          ],
        );
        if (focusFailure != null) {
          failures.add(
            'Step 2 failed: keyboard Tab traversal did not stay in logical top-to-bottom order. '
            '$focusFailure Observed Tab order: ${forwardFocusOrder.join(' -> ')}.',
          );
        }

        await screen.clearSummary();
        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          isEmpty,
          reason:
              'TS-402 must clear the Summary field before checking the empty-state placeholder contrast and validation feedback.',
        );
        await screen.focusField('Description');

        final placeholderObservation = screen
            .observeSummaryPlaceholderContrast();
        if (placeholderObservation.contrastRatio < 3.0) {
          failures.add(
            'Step 5 failed: the empty Summary placeholder contrast was ${placeholderObservation.describe()}, '
            'below the required 3.0:1 threshold for placeholder text.',
          );
        }

        await screen.submit();

        final validationTexts = screen.visibleTexts();
        final validationSemantics = screen.visibleSemanticsLabels();
        final accessibilityFeedback = screen.accessibilityFeedbackTexts();
        const validationMessage = 'Summary is required before saving.';
        final validationVisible = _containsLabel(
          validationTexts,
          validationMessage,
        );
        if (!validationVisible) {
          failures.add(
            'Step 4 failed: submitting the Edit issue form with an empty Summary did not render the visible validation message "$validationMessage". '
            'Visible edit-surface text: ${_formatSnapshot(validationTexts)}.',
          );
        }

        final focusedLabel = screen.focusedSemanticsLabel();
        final validationAnnounced = _containsSummaryRequiredFeedback(
          accessibilityFeedback,
        );
        final focusReturnedToSummary =
            focusedLabel == 'Summary' ||
            (focusedLabel ?? '').startsWith('Summary ');
        if (!focusReturnedToSummary && !validationAnnounced) {
          failures.add(
            'Step 4 failed: after the summary-required validation error, focus did not return to Summary and no summary-required message was exposed in visible semantics. '
            'Focused semantics label: ${focusedLabel ?? '<none>'}. '
            'Visible semantics labels: ${_formatSnapshot(validationSemantics)}. '
            'Accessibility feedback text: ${_formatSnapshot(accessibilityFeedback)}.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        await screen?.dispose();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

String? _orderedSubsequenceFailure(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = _indexOfLabel(observed, label);
    if (index == -1) {
      return 'The accessibility order did not expose "$label" as a reachable target.';
    }
    if (index <= previousIndex) {
      return 'The accessibility order did not keep the edit controls in logical top-to-bottom order.';
    }
    previousIndex = index;
  }
  return null;
}

int _indexOfLabel(List<String> observed, String label) {
  for (var index = 0; index < observed.length; index += 1) {
    final candidate = observed[index];
    if (candidate == label || candidate.startsWith('$label ')) {
      return index;
    }
  }
  return -1;
}

bool _containsLabel(List<String> observed, String label) {
  return _indexOfLabel(observed, label) != -1;
}

bool _containsSummaryRequiredFeedback(List<String> observed) {
  for (final value in observed) {
    final normalized = value.toLowerCase();
    if (normalized.contains('summary') && normalized.contains('required')) {
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
