import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import '../testing/core/interfaces/issue_edit_accessibility_screen.dart';
import '../testing/fixtures/issue_edit_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'edit issue Summary field no longer uses a manual semantics wrapper',
    (tester) async {
      final semanticsHandle = tester.ensureSemantics();
      IssueEditAccessibilityScreenHandle? screen;

      try {
        screen = await launchIssueEditAccessibilityFixture(tester);

        final summaryTextField = find.byWidgetPredicate(
          (widget) =>
              widget is TextField && widget.decoration?.labelText == 'Summary',
          description: 'Summary text field',
        );
        expect(summaryTextField, findsOneWidget);

        final manualWrappingSemantics = find.ancestor(
          of: summaryTextField,
          matching: find.byWidgetPredicate((widget) {
            return widget is Semantics &&
                widget.properties.label == 'Summary' &&
                widget.properties.textField == true;
          }, description: 'manual Summary semantics wrapper'),
        );

        expect(manualWrappingSemantics, findsNothing);
      } finally {
        await screen?.dispose();
        semanticsHandle.dispose();
      }
    },
  );
}
