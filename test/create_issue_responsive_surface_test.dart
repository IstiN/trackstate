import 'package:flutter_test/flutter_test.dart';

import '../testing/core/interfaces/create_issue_accessibility_screen.dart';
import '../testing/fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'create issue surface docks on desktop and expands on compact resize',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        final desktopLayout = screen.observeLayout();
        expect(desktopLayout.widthFraction, lessThanOrEqualTo(0.5));
        expect(desktopLayout.rightInset, lessThanOrEqualTo(48));
        expect(desktopLayout.leftInset, greaterThanOrEqualTo(200));
        expect(tester.takeException(), isNull);

        await screen.resizeToViewport(width: 390, height: 844);

        final compactLayout = screen.observeLayout();
        expect(compactLayout.widthFraction, greaterThanOrEqualTo(0.9));
        expect(compactLayout.heightFraction, greaterThanOrEqualTo(0.9));
        expect(compactLayout.leftInset, lessThanOrEqualTo(24));
        expect(compactLayout.rightInset, lessThanOrEqualTo(24));
        expect(compactLayout.topInset, lessThanOrEqualTo(24));
        expect(compactLayout.bottomInset, lessThanOrEqualTo(24));
        expect(tester.takeException(), isNull);
      } finally {
        await screen?.dispose();
        semantics.dispose();
      }
    },
  );
}
