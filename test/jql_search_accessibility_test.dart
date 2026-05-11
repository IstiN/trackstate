import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/jql_search_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'search pagination exposes distinct semantics, focus order, and AC5 button tokens',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final screen = await launchJqlSearchAccessibilityFixture(tester);
        await screen.openSearch();

        expect(screen.countExactSemanticsLabel('Search issues'), 1);
        expect(screen.countExactSemanticsLabel('Load more issues'), 1);

        expect(await screen.collectForwardFocusOrder(), [
          'Search issues',
          for (var index = 1; index <= 6; index += 1)
            'Open TRACK-$index Paged issue $index',
          'Load more issues',
        ]);
        expect(await screen.collectBackwardFocusOrder(), [
          'Load more issues',
          for (var index = 6; index >= 1; index -= 1)
            'Open TRACK-$index Paged issue $index',
          'Search issues',
        ]);

        final idleObservation = screen.observeLoadMoreButtonIdle();
        expect(idleObservation.usesExpectedBaseTokens, isTrue);
        expect(idleObservation.contrastRatio, greaterThanOrEqualTo(4.5));

        expect(
          screen.observeLoadMoreButtonHovered().usesExpectedInteractionTokens,
          isTrue,
        );
        expect(
          screen.observeLoadMoreButtonFocused().usesExpectedInteractionTokens,
          isTrue,
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
