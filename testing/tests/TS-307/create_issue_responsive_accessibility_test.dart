import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-307 adapts the Create issue surface responsively and keeps it accessible',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        final failures = <String>[];

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
          'Optional',
          'Save',
          'Cancel',
        ]) {
          if (!screen.showsText(text)) {
            failures.add(
              'The visible Create issue surface did not render "$text". '
              'Visible Create issue texts: ${screen.visibleTexts().join(' | ')}.',
            );
          }
        }

        final desktopLayout = screen.observeLayout();
        final wideLooksLikeSideSheet =
            desktopLayout.widthFraction <= 0.5 &&
            desktopLayout.rightInset <= 48 &&
            desktopLayout.leftInset >= 200;
        if (!wideLooksLikeSideSheet) {
          failures.add(
            'On a wide desktop viewport, Create issue should appear as a right-docked side sheet, '
            'but the rendered surface looked like ${desktopLayout.describe()}.',
          );
        }

        final traversal = screen.semanticsTraversal();
        final traversalFailure = _logicalFieldOrderFailure(
          traversal,
          expectedOrder: const [
            'Issue Type',
            'Summary',
            'Description',
            'Priority',
            'Initial status',
            'Epic',
            'Assignee',
            'Labels',
          ],
        );
        if (traversalFailure != null) {
          failures.add(
            '$traversalFailure Observed accessibility traversal: ${traversal.join(' -> ')}.',
          );
        }

        for (final text in const [
          'Summary',
          'Description',
          'Priority',
          'Initial status',
          'Epic',
          'Assignee',
          'Labels',
          'Optional',
        ]) {
          final observation = screen.observeTextContrast(text);
          if (observation.contrastRatio < 4.5) {
            failures.add(
              'Visible "${observation.text}" contrast was ${observation.describe()}, '
              'below the required 4.5:1 threshold for normal text.',
            );
          }
        }

        await screen.resizeToViewport(width: 390, height: 844);

        final compactLayout = screen.observeLayout();
        final compactLooksFullScreen =
            compactLayout.widthFraction >= 0.9 &&
            compactLayout.heightFraction >= 0.9 &&
            compactLayout.leftInset <= 24 &&
            compactLayout.rightInset <= 24 &&
            compactLayout.topInset <= 24 &&
            compactLayout.bottomInset <= 24;
        if (!compactLooksFullScreen) {
          failures.add(
            'On a compact viewport, Create issue should switch to a full-screen surface, '
            'but the rendered surface looked like ${compactLayout.describe()}.',
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

String? _logicalFieldOrderFailure(
  List<String> traversal, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = _indexOfTraversalLabel(traversal, label);
    if (index == -1) {
      return 'The Create issue accessibility traversal did not expose "$label" as a screen-reader target.';
    }
    if (index <= previousIndex) {
      return 'The Create issue accessibility traversal did not keep the visible form fields in top-to-bottom order.';
    }
    previousIndex = index;
  }
  return null;
}

int _indexOfTraversalLabel(List<String> traversal, String label) {
  for (var index = 0; index < traversal.length; index++) {
    final candidate = traversal[index];
    if (candidate == label || candidate.startsWith('$label ')) {
      return index;
    }
  }
  return -1;
}
