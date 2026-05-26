import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../core/models/create_issue_layout_observation.dart';
import '../../core/models/create_issue_scroll_observation.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-395 Create issue initializes at 1440x640 with scrolling already enabled',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      const initialVisibleTexts = <String>[
        'Create issue',
        'Issue Type',
        'Summary',
        'Description',
        'Priority',
        'Initial status',
      ];

      try {
        screen = await launchCreateIssueAccessibilityFixture(
          tester,
          initialViewportWidth: 1440,
          initialViewportHeight: 640,
        );

        final failures = <String>[];

        final initialLayout = screen.observeLayout();
        final initialVisibleTextSnapshot = screen.visibleTexts();
        final initialScroll = screen.observeVerticalScroll();
        final initialExceptions = _drainFrameworkExceptions(tester);

        if (initialExceptions.isNotEmpty) {
          failures.add(
            'Steps 2 and 5 failed at viewport 1440x640: opening the Create '
            'issue form surfaced framework exceptions during the initial build '
            'instead of initializing with vertical scrolling. Observed layout: '
            '${initialLayout.describe()}. Visible Create issue texts: '
            '${initialVisibleTextSnapshot.join(' | ')}.\nExceptions:\n'
            '${initialExceptions.join('\n---\n')}',
          );
        }

        final missingTexts = initialVisibleTexts
            .where((text) => !screen!.showsText(text))
            .toList(growable: false);
        if (missingTexts.isNotEmpty) {
          failures.add(
            'Step 1 failed at viewport 1440x640: opening the Create issue form '
            'did not render ${missingTexts.map((text) => '"$text"').join(', ')} '
            'in the visible surface. Visible Create issue texts: '
            '${initialVisibleTextSnapshot.join(' | ')}.',
          );
        }

        final boundsFailure = _layoutBoundsFailure(initialLayout);
        if (boundsFailure != null) {
          failures.add(
            'Step 2 failed at viewport 1440x640: $boundsFailure Observed '
            'layout: ${initialLayout.describe()}.',
          );
        }

        if (!initialScroll.hasOverflow) {
          failures.add(
            'Step 3 failed at viewport 1440x640: the Create issue form should '
            'expose vertical scrolling on initial load, but '
            '${initialScroll.describe()} was observed.',
          );
        }

        if (initialScroll.isScrolled) {
          failures.add(
            'Step 3 failed at viewport 1440x640: the Create issue form should '
            'open at the top of the scrollable content, but '
            '${initialScroll.describe()} was observed.',
          );
        }

        await screen.scrollToBottom();
        final bottomScroll = screen.observeVerticalScroll();
        final saveVisible = screen.isTextVisibleInViewport('Save');
        final cancelVisible = screen.isTextVisibleInViewport('Cancel');
        final bottomExceptions = _drainFrameworkExceptions(tester);

        if (!bottomScroll.isScrolled || !bottomScroll.isAtBottom) {
          failures.add(
            'Step 4 failed at viewport 1440x640: scrolling to the bottom '
            'should move the Create issue body to its final extent, but '
            '${bottomScroll.describe()} was observed.',
          );
        }

        if (!saveVisible || !cancelVisible) {
          failures.add(
            'Step 4 failed at viewport 1440x640: after scrolling to the '
            'bottom, the user should be able to reach both action buttons, but '
            'Save=${saveVisible ? 'visible' : 'missing'} and '
            'Cancel=${cancelVisible ? 'visible' : 'missing'}. Visible Create '
            'issue texts: ${screen.visibleTexts().join(' | ')}. Scroll state: '
            '${bottomScroll.describe()}.',
          );
        }

        if (bottomExceptions.isNotEmpty) {
          failures.add(
            'Step 5 failed at viewport 1440x640: interacting with the Create '
            'issue scrollable area still triggered framework exceptions.\n'
            'Exceptions:\n${bottomExceptions.join('\n---\n')}',
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

String? _layoutBoundsFailure(CreateIssueLayoutObservation layout) {
  const epsilon = 0.5;

  if (layout.surfaceWidth <= 0 || layout.surfaceHeight <= 0) {
    return 'The Create issue surface collapsed to a non-visible size.';
  }
  if (layout.leftInset < -epsilon || layout.topInset < -epsilon) {
    return 'The Create issue surface shifted outside the visible viewport origin.';
  }
  if (layout.rightInset < -epsilon || layout.bottomInset < -epsilon) {
    return 'The Create issue surface overflowed beyond the visible viewport bounds.';
  }

  return null;
}

List<String> _drainFrameworkExceptions(WidgetTester tester) {
  final messages = <String>[];
  Object? exception;
  while ((exception = tester.takeException()) != null) {
    messages.add(exception.toString());
  }
  return messages;
}
