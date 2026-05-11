import 'package:flutter_test/flutter_test.dart';

import '../testing/core/interfaces/create_issue_accessibility_screen.dart';
import '../testing/fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'create issue surface keeps resizing cleanly through intermediate breakpoints',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      const requiredTexts = <String>[
        'Create issue',
        'Summary',
        'Description',
        'Save',
        'Cancel',
      ];
      const resizePath = <({double width, double height})>[
        (width: 1440, height: 960),
        (width: 1280, height: 960),
        (width: 1120, height: 960),
        (width: 960, height: 900),
        (width: 840, height: 900),
        (width: 720, height: 844),
        (width: 600, height: 844),
        (width: 520, height: 844),
        (width: 460, height: 844),
        (width: 390, height: 844),
      ];

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        for (final viewport in resizePath) {
          await screen.resizeToViewport(
            width: viewport.width,
            height: viewport.height,
          );

          expect(
            _drainFrameworkExceptions(tester),
            isEmpty,
            reason:
                'Unexpected framework exceptions while resizing to '
                '${viewport.width.toStringAsFixed(0)}x'
                '${viewport.height.toStringAsFixed(0)}.',
          );
          for (final text in requiredTexts) {
            expect(
              screen.showsText(text),
              isTrue,
              reason:
                  'Expected "$text" to remain visible at '
                  '${viewport.width.toStringAsFixed(0)}x'
                  '${viewport.height.toStringAsFixed(0)}.',
            );
          }
        }
      } finally {
        await screen?.dispose();
        semantics.dispose();
      }
    },
  );

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

  testWidgets(
    'create issue surface scrolls instead of overflowing during desktop height reduction',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        await screen.resizeToViewport(width: 1440, height: 640);

        expect(
          _drainFrameworkExceptions(tester),
          isEmpty,
          reason:
              'Reducing only the desktop viewport height should not trigger '
              'RenderFlex overflow exceptions.',
        );

        await screen.resizeToViewport(width: 1440, height: 400);

        final scrollState = screen.observeVerticalScroll();
        expect(
          scrollState.hasOverflow,
          isTrue,
          reason:
              'The Create issue body should become vertically scrollable at '
              'short desktop heights.',
        );

        await screen.scrollToBottom();

        expect(screen.isTextVisibleInViewport('Save'), isTrue);
        expect(screen.isTextVisibleInViewport('Cancel'), isTrue);
        expect(_drainFrameworkExceptions(tester), isEmpty);
      } finally {
        await screen?.dispose();
        semantics.dispose();
      }
    },
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
