import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  const desktopViewportWidth = 1440.0;
  const desktopViewportHeight = 900.0;
  testWidgets(
    'TS-334 Create issue desktop surface is flush with the right viewport edge',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      try {
        screen = await launchCreateIssueAccessibilityFixture(
          tester,
          initialViewportWidth: desktopViewportWidth,
          initialViewportHeight: desktopViewportHeight,
        );
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
          'Save',
          'Cancel',
        ]) {
          if (!screen.showsText(text)) {
            failures.add(
              'The user-visible Create issue desktop surface should show "$text". '
              'Visible texts: ${screen.visibleTexts().join(' | ')}.',
            );
          }
        }

        final layout = screen.observeLayout();
        final rightEdge = layout.surfaceLeft + layout.surfaceWidth;

        if (layout.viewportWidth != desktopViewportWidth) {
          failures.add(
            'TS-334 validates the desktop Create issue layout at '
            '${desktopViewportWidth.toStringAsFixed(0)}px width, '
            'but observed ${layout.viewportWidth.toStringAsFixed(0)}px.',
          );
        }
        if (layout.viewportHeight != desktopViewportHeight) {
          failures.add(
            'TS-334 uses the default desktop viewport height of '
            '${desktopViewportHeight.toStringAsFixed(0)}px because the ticket '
            'only specifies a 1440px-wide desktop viewport, but observed '
            '${layout.viewportHeight.toStringAsFixed(0)}px.',
          );
        }
        if (layout.widthFraction < 0.3 || layout.widthFraction > 0.5) {
          failures.add(
            'The desktop Create issue surface should stay a side sheet instead of '
            'stretching full-width or collapsing into a centered card. '
            'Observed ${layout.describe()}.',
          );
        }
        if (layout.leftInset < 200) {
          failures.add(
            'The desktop Create issue surface should remain docked on the right side '
            'with a substantial left inset. Observed ${layout.describe()}.',
          );
        }
        if ((layout.rightInset - 0).abs() > 0.5) {
          failures.add(
            'Expected: a numeric value within <0.5> of <0>\n'
            '  Actual: <${layout.rightInset.toStringAsFixed(1)}>\n'
            '   Which: differs by <${layout.rightInset.abs().toStringAsFixed(1)}>\n'
            'The desktop Create issue surface should be flush with the right viewport '
            'edge, but ${layout.describe()} was rendered.',
          );
        }
        if ((rightEdge - layout.viewportWidth).abs() > 0.5) {
          failures.add(
            'The Create issue surface right edge should align with the viewport width, '
            'but rightEdge=${rightEdge.toStringAsFixed(1)} and '
            'viewportWidth=${layout.viewportWidth.toStringAsFixed(1)} were observed. '
            'Rendered ${layout.describe()}.',
          );
        }
        if (layout.rightInset >= 24) {
          failures.add(
            'The previous 276px desktop inset regression should stay fixed, but '
            'the rendered surface still leaves a ${layout.rightInset.toStringAsFixed(1)}px '
            'right inset. Observed ${layout.describe()}.',
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
