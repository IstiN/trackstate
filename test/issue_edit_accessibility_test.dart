import 'package:flutter_test/flutter_test.dart';

import '../testing/core/interfaces/issue_edit_accessibility_screen.dart';
import '../testing/fixtures/issue_edit_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'edit issue flow keeps labels, focus order, and validation feedback accessible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      IssueEditAccessibilityScreenHandle? screen;

      try {
        screen = await launchIssueEditAccessibilityFixture(tester);

        for (final text in const [
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
          expect(
            screen.showsText(text),
            isTrue,
            reason: 'Expected the Edit issue surface to show "$text".',
          );
        }

        final semanticsLabels = screen.visibleSemanticsLabels();
        for (final label in const [
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
          expect(
            _containsLabel(semanticsLabels, label),
            isTrue,
            reason: 'Expected a visible semantics label for "$label".',
          );
        }

        final semanticsTraversal = screen.semanticsTraversal();
        expect(
          _orderedSubsequenceFailure(
            semanticsTraversal,
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
          ),
          isNull,
          reason:
              'Observed screen-reader order: ${semanticsTraversal.join(' -> ')}',
        );

        final focusOrder = await screen.collectForwardFocusOrder();
        expect(
          _orderedSubsequenceFailure(
            focusOrder,
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
          ),
          isNull,
          reason: 'Observed Tab order: ${focusOrder.join(' -> ')}',
        );

        await screen.clearSummary();
        expect(await screen.readLabeledTextFieldValue('Summary'), isEmpty);
        await screen.focusField('Description');
        expect(
          screen.observeSummaryPlaceholderContrast().contrastRatio,
          greaterThanOrEqualTo(3.0),
        );

        await screen.submit();

        expect(
          _containsLabel(
            screen.visibleTexts(),
            'Summary is required before saving.',
          ),
          isTrue,
        );

        final focusedLabel = screen.focusedSemanticsLabel();
        final feedback = screen.accessibilityFeedbackTexts();
        final focusReturnedToSummary =
            focusedLabel == 'Summary' ||
            (focusedLabel ?? '').startsWith('Summary ');
        final summaryRequiredAnnounced = feedback.any((value) {
          final normalized = value.toLowerCase();
          return normalized.contains('summary') &&
              normalized.contains('required');
        });
        expect(focusReturnedToSummary || summaryRequiredAnnounced, isTrue);
      } finally {
        await screen?.dispose();
        semantics.dispose();
      }
    },
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
      return 'Missing "$label" in accessibility order.';
    }
    if (index <= previousIndex) {
      return 'Accessibility order regressed at "$label".';
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
