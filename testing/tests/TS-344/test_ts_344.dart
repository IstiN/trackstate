import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../core/models/create_issue_layout_observation.dart';
import '../../core/models/create_issue_scroll_observation.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-344 Create issue height reduction enables scrolling without bottom overflow',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      const persistentTexts = <String>[
        'Create issue',
        'Summary',
        'Description',
      ];
      const resizePath = <double>[960, 800, 640, 520, 400];

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        final failures = <String>[];
        CreateIssueScrollObservation? shortestViewportScroll;

        for (final height in resizePath) {
          await screen.resizeToViewport(width: 1440, height: height);

          final layout = screen.observeLayout();
          final visibleTexts = screen.visibleTexts();
          final exceptions = _drainFrameworkExceptions(tester);

          if (exceptions.isNotEmpty) {
            failures.add(
              'Step 5 failed at viewport 1440x${height.toStringAsFixed(0)}: '
              'reducing the Create issue form height surfaced framework exceptions '
              'instead of adapting with vertical scrolling. '
              'Observed layout: ${layout.describe()}. '
              'Visible Create issue texts: ${visibleTexts.join(' | ')}.\n'
              'Exceptions:\n${exceptions.join('\n---\n')}',
            );
          }

          final missingTexts = persistentTexts
              .where((text) => !screen!.showsText(text))
              .toList(growable: false);
          if (missingTexts.isNotEmpty) {
            failures.add(
              'Step 2 failed at viewport 1440x${height.toStringAsFixed(0)}: '
              'the visible Create issue form stopped rendering '
              '${missingTexts.map((text) => '"$text"').join(', ')} while the '
              'height was reduced. Visible Create issue texts: '
              '${visibleTexts.join(' | ')}.',
            );
          }

          final boundsFailure = _layoutBoundsFailure(layout);
          if (boundsFailure != null) {
            failures.add(
              'Step 2 failed at viewport 1440x${height.toStringAsFixed(0)}: '
              '$boundsFailure Observed layout: ${layout.describe()}.',
            );
          }

          if (height == 400) {
            shortestViewportScroll = screen.observeVerticalScroll();
          }
        }

        final finalScroll = shortestViewportScroll;
        if (finalScroll == null) {
          failures.add(
            'Test setup failed: the 1440x400 viewport observation was not captured.',
          );
        } else if (!finalScroll.hasOverflow) {
          failures.add(
            'Step 3 failed at viewport 1440x400: reducing the Create issue form '
            'height should expose vertical scrolling so the remaining fields stay '
            'accessible, but ${finalScroll.describe()} was observed.',
          );
        }

        await screen.scrollToBottom();
        final scrolledState = screen.observeVerticalScroll();
        final saveVisible = screen.isTextVisibleInViewport('Save');
        final cancelVisible = screen.isTextVisibleInViewport('Cancel');

        if (!scrolledState.isScrolled || !scrolledState.isAtBottom) {
          failures.add(
            'Step 4 failed at viewport 1440x400: scrolling to the bottom should '
            'move the Create issue body to its final extent, but '
            '${scrolledState.describe()} was observed.',
          );
        }

        if (!saveVisible || !cancelVisible) {
          failures.add(
            'Step 4 failed at viewport 1440x400: after scrolling to the bottom, '
            'the user should be able to reach both action buttons, but '
            'Save=${saveVisible ? 'visible' : 'missing'} and '
            'Cancel=${cancelVisible ? 'visible' : 'missing'}. '
            'Visible Create issue texts: ${screen.visibleTexts().join(' | ')}. '
            'Scroll state: ${scrolledState.describe()}.',
          );
        }

        final postScrollExceptions = _drainFrameworkExceptions(tester);
        if (postScrollExceptions.isNotEmpty) {
          failures.add(
            'Expected Result failed at viewport 1440x400: scrolling the Create '
            'issue body to the bottom still triggered framework exceptions.\n'
            'Exceptions:\n${postScrollExceptions.join('\n---\n')}',
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
