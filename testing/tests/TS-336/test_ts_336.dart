import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../core/models/create_issue_layout_observation.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-336 resizes Create issue from desktop to mobile without RenderFlex overflow',
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

        final failures = <String>[];

        for (final viewport in resizePath) {
          await screen.resizeToViewport(
            width: viewport.width,
            height: viewport.height,
          );

          final layout = screen.observeLayout();
          final visibleTexts = screen.visibleTexts();
          final exceptions = _drainFrameworkExceptions(tester);

          if (exceptions.isNotEmpty) {
            failures.add(
              'Step 3 failed at viewport '
              '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
              'resizing the open Create issue form surfaced framework exceptions '
              'instead of adapting cleanly. '
              'Observed layout: ${layout.describe()}. '
              'Visible Create issue texts: ${visibleTexts.join(' | ')}.\n'
              'Exceptions:\n${exceptions.join('\n---\n')}',
            );
          }

          final missingTexts = requiredTexts
              .where((text) => !screen!.showsText(text))
              .toList(growable: false);
          if (missingTexts.isNotEmpty) {
            failures.add(
              'Step 2 failed at viewport '
              '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
              'the user-visible Create issue form stopped showing '
              '${missingTexts.map((text) => '"$text"').join(', ')}. '
              'Visible Create issue texts: ${visibleTexts.join(' | ')}.',
            );
          }

          final boundsFailure = _layoutBoundsFailure(layout);
          if (boundsFailure != null) {
            failures.add(
              'Step 1 failed at viewport '
              '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
              '$boundsFailure Observed layout: ${layout.describe()}.',
            );
          }
        }

        final finalLayout = screen.observeLayout();
        final compactLooksFullScreen =
            finalLayout.widthFraction >= 0.9 &&
            finalLayout.heightFraction >= 0.9 &&
            finalLayout.leftInset <= 24 &&
            finalLayout.rightInset <= 24 &&
            finalLayout.topInset <= 24 &&
            finalLayout.bottomInset <= 24;
        if (!compactLooksFullScreen) {
          failures.add(
            'Expected Result failed at 390x844: after the full desktop-to-mobile resize, '
            'Create issue should remain readable as a compact full-screen surface, '
            'but it rendered as ${finalLayout.describe()}.',
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
