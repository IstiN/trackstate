@TestOn('browser')
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/services/browser_focusable_control_stub.dart'
    if (dart.library.js_interop) 'package:trackstate/ui/features/tracker/services/browser_focusable_control_web.dart'
    as browser_focusable_control;

void main() {
  testWidgets(
    'browser focusable control removes the wrapped Flutter child from focus traversal',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 220,
              child: browser_focusable_control.BrowserFocusableControl(
                label: 'Save and switch',
                onPressed: () {},
                focusTargetId: 'workspace-save-and-switch',
                panelId: 'workspace-switcher',
                child: FilledButton(
                  onPressed: () {},
                  child: const Text('Save and switch'),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final focusGuards = tester.widgetList<Focus>(
        find.descendant(
          of: find.byType(browser_focusable_control.BrowserFocusableControl),
          matching: find.byType(Focus),
        ),
      );

      expect(
        focusGuards.any(
          (focus) =>
              focus.skipTraversal &&
              !focus.canRequestFocus &&
              !focus.descendantsAreFocusable &&
              !focus.descendantsAreTraversable,
        ),
        isTrue,
        reason:
            'The wrapped Flutter child must be removed from web focus '
            'traversal so browser Tab order uses only the focus-bridge '
            'element.',
      );
    },
  );
}
