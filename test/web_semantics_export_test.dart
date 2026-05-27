import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'collaboration tabs use explicit semantics wrappers for web export',
    (tester) async {
      final semantics = tester.ensureSemantics();

      Finder byExactSemanticsLabel(String label) => find.byWidgetPredicate(
        (widget) =>
            widget is Semantics &&
            widget.properties.label == label &&
            widget.properties.button == true,
      );

      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;
        final screen = await launchIssueDetailAccessibilityFixture(tester);
        await screen.openSearch();
        await screen.selectIssue('TRACK-12', 'Implement Git sync service');

        for (final label in const ['Detail', 'Comments', 'Attachments', 'History']) {
          final tab = tester.widget<Semantics>(byExactSemanticsLabel(label));
          expect(
            tab.properties.button,
            isTrue,
            reason: 'The $label collaboration tab should export as a button semantics node.',
          );
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
