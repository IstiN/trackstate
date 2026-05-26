import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-334 Create issue desktop surface is flush with the right viewport edge',
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
            reason:
                'The user-visible Create issue desktop surface should show "$text". '
                'Visible texts: ${screen.visibleTexts().join(' | ')}.',
          );
        }

        final layout = screen.observeLayout();
        final rightEdge = layout.surfaceLeft + layout.surfaceWidth;

        expect(
          layout.viewportWidth,
          1440,
          reason:
              'TS-334 validates the desktop Create issue layout at 1440px width.',
        );
        expect(
          layout.viewportHeight,
          960,
          reason:
              'TS-334 validates the desktop Create issue layout at 960px height.',
        );
        expect(
          layout.widthFraction,
          inInclusiveRange(0.3, 0.5),
          reason:
              'The desktop Create issue surface should stay a side sheet instead of '
              'stretching full-width or collapsing into a centered card. '
              'Observed ${layout.describe()}.',
        );
        expect(
          layout.leftInset,
          greaterThanOrEqualTo(200),
          reason:
              'The desktop Create issue surface should remain docked on the right side '
              'with a substantial left inset. Observed ${layout.describe()}.',
        );
        expect(
          layout.rightInset,
          closeTo(0, 0.5),
          reason:
              'The desktop Create issue surface should be flush with the right viewport '
              'edge, but ${layout.describe()} was rendered.',
        );
        expect(
          rightEdge,
          closeTo(layout.viewportWidth, 0.5),
          reason:
              'The Create issue surface right edge should align with the viewport width, '
              'but ${layout.describe()} was rendered.',
        );
        expect(
          layout.rightInset,
          lessThan(24),
          reason:
              'The prior large desktop gap regression should stay fixed; '
              '${layout.describe()} still leaves a visible right inset.',
        );
      } finally {
        await screen?.dispose();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}
