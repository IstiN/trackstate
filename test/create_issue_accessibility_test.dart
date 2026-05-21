import 'package:flutter_test/flutter_test.dart';

import '../testing/core/interfaces/create_issue_accessibility_screen.dart';
import '../testing/fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'create issue flow keeps visible controls labeled and ordered across required layouts',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        for (final text in const [
          'Create issue',
          'Issue Type',
          'Summary',
          'Description',
          'Priority',
          'Initial status',
          'Epic',
          'Assignee',
          'Labels',
          'Save',
          'Cancel',
        ]) {
          expect(
            screen.showsText(text),
            isTrue,
            reason: 'Expected the Create issue surface to show "$text".',
          );
        }

        final semanticsLabels = screen.visibleSemanticsLabels();
        for (final label in const [
          'Issue Type',
          'Summary',
          'Description',
          'Priority',
          'Initial status',
          'Epic',
          'Assignee',
          'Labels',
          'Save',
          'Cancel',
        ]) {
          expect(
            _containsLabel(semanticsLabels, label),
            isTrue,
            reason: 'Expected a visible semantics label for "$label".',
          );
        }

        expect(
          _orderedSubsequenceFailure(
            screen.semanticsTraversal(),
            expectedOrder: const [
              'Issue Type',
              'Summary',
              'Description',
              'Priority',
              'Initial status',
              'Epic',
              'Assignee',
              'Labels',
              'Save',
              'Cancel',
            ],
          ),
          isNull,
        );

        for (final text in const [
          'Summary',
          'Description',
          'Priority',
          'Initial status',
          'Assignee',
          'Labels',
        ]) {
          expect(
            screen.observeTextContrast(text).contrastRatio,
            greaterThanOrEqualTo(4.5),
            reason: 'Expected "$text" to meet WCAG AA contrast.',
          );
        }

        await screen.resizeToViewport(width: 390, height: 844);

        final compactLayout = screen.observeLayout();
        expect(compactLayout.widthFraction, greaterThanOrEqualTo(0.9));
        expect(compactLayout.heightFraction, greaterThanOrEqualTo(0.9));
        expect(screen.showsText('Save'), isTrue);
        expect(screen.showsText('Cancel'), isTrue);
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
      return 'Missing "$label" in semantics traversal.';
    }
    if (index <= previousIndex) {
      return 'Traversal order is not top-to-bottom for "$label".';
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
