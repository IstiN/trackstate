import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-335 opens Create issue full-screen on a 390x844 viewport',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      try {
        screen = await launchCreateIssueAccessibilityFixture(
          tester,
          initialViewportWidth: 390,
          initialViewportHeight: 844,
        );

        final failures = <String>[];

        for (final text in const [
          'Create issue',
          'Issue Type',
          'Summary',
          'Description',
          'Priority',
          'Initial status',
          'Save',
          'Cancel',
        ]) {
          if (!screen.showsText(text)) {
            failures.add(
              'Step 2 failed: after opening Create issue on a 390x844 viewport, '
              'the visible form did not show "$text". '
              'Visible Create issue texts: ${screen.visibleTexts().join(' | ')}.',
            );
          }
        }

        final layout = screen.observeLayout();
        if ((layout.viewportWidth - 390).abs() > 0.1 ||
            (layout.viewportHeight - 844).abs() > 0.1) {
          failures.add(
            'Step 1 failed: the viewport should be 390x844 before opening Create issue, '
            'but ${layout.describe()} was observed.',
          );
        }

        const epsilon = 0.5;
        if ((layout.surfaceLeft - 0).abs() > epsilon ||
            (layout.surfaceTop - 0).abs() > epsilon ||
            (layout.surfaceWidth - 390).abs() > epsilon ||
            (layout.surfaceHeight - 844).abs() > epsilon) {
          failures.add(
            'Step 3 failed: inspecting the Create issue surface should show a full-screen '
            '390x844 surface at coordinates (0,0), but ${layout.describe()} was rendered.',
          );
        }

        if (layout.leftInset.abs() > epsilon ||
            layout.rightInset.abs() > epsilon ||
            layout.topInset.abs() > epsilon ||
            layout.bottomInset.abs() > epsilon) {
          failures.add(
            'Expected Result failed: no side or bottom inset should remain on the mobile '
            'Create issue surface, but ${layout.describe()} was rendered.',
          );
        }

        final exceptions = _drainFrameworkExceptions(tester);
        if (exceptions.isNotEmpty) {
          failures.add(
            'Opening Create issue on the 390x844 viewport surfaced framework exceptions '
            'instead of a clean full-screen layout.\n'
            'Exceptions:\n${exceptions.join('\n---\n')}',
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

List<String> _drainFrameworkExceptions(WidgetTester tester) {
  final messages = <String>[];
  Object? exception;
  while ((exception = tester.takeException()) != null) {
    messages.add(exception.toString());
  }
  return messages;
}
