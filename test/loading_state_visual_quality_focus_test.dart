import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/loading_state_visual_quality_screen_fixture.dart';

void main() {
  testWidgets(
    'loading-state keyboard traversal reaches visible shell controls and bootstrap result rows',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = await launchLoadingStateVisualQualityFixture(tester);

      try {
        await screen.openJqlSearch();

        final focusVisits = await screen.collectLoadingFocusVisits(tabs: 40);

        expect(
          focusVisits,
          containsAll(<String>[
            'Create issue',
            'Connect GitHub',
            'JQL Search navigation',
            'Search issues field',
            'First loading result',
          ]),
        );
      } finally {
        screen.dispose();
        semantics.dispose();
      }
    },
  );
}
