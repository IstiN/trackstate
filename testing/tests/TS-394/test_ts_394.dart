import 'dart:ui' show Rect;

import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../core/models/create_issue_layout_observation.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-394 Create issue validation stays scrollable at 1440x400 without overflow',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      const viewportWidth = 1440.0;
      const viewportHeight = 400.0;
      const summaryValidationMessage = 'Summary is required before saving.';

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        final failures = <String>[];

        await screen.resizeToViewport(
          width: viewportWidth,
          height: viewportHeight,
        );

        final initialLayout = screen.observeLayout();
        final initialScroll = screen.observeVerticalScroll();
        final descriptionRectBefore = screen.observeLabeledTextFieldRect(
          'Description',
        );
        final initialSummary = await screen.readLabeledTextFieldValue(
          'Summary',
        );
        final initialExceptions = _drainFrameworkExceptions(tester);

        if (initialExceptions.isNotEmpty) {
          failures.add(
            'Steps 1 and 6 failed at viewport 1440x400: opening the Create '
            'issue form at the minimum supported height surfaced framework '
            'exceptions before validation was triggered. Observed layout: '
            '${initialLayout.describe()}. Visible Create issue texts: '
            '${screen.visibleTexts().join(' | ')}.\nExceptions:\n'
            '${initialExceptions.join('\n---\n')}',
          );
        }

        final boundsFailure = _layoutBoundsFailure(initialLayout);
        if (boundsFailure != null) {
          failures.add(
            'Step 1 failed at viewport 1440x400: $boundsFailure Observed '
            'layout: ${initialLayout.describe()}.',
          );
        }

        if (!initialScroll.hasOverflow) {
          failures.add(
            'Step 1 failed at viewport 1440x400: the Create issue form should '
            'already expose vertical scrolling at the minimum supported height, '
            'but ${initialScroll.describe()} was observed.',
          );
        }

        if (initialSummary != '') {
          failures.add(
            'Step 2 failed: the Summary field should start empty before the '
            'validation attempt, but ${initialSummary == null ? 'it was not readable' : '"$initialSummary" was rendered'}. '
            'Visible Create issue texts: ${screen.visibleTexts().join(' | ')}.',
          );
        }

        if (descriptionRectBefore == null) {
          failures.add(
            'Step 2 failed: the visible Description field was not readable '
            'before validation. Visible Create issue texts: '
            '${screen.visibleTexts().join(' | ')}.',
          );
        }

        await screen.scrollToBottom();
        final preValidationBottomScroll = screen.observeVerticalScroll();
        final saveVisibleBeforeValidation = screen.isTextVisibleInViewport(
          'Save',
        );
        final cancelVisibleBeforeValidation = screen.isTextVisibleInViewport(
          'Cancel',
        );

        if (!preValidationBottomScroll.isScrolled ||
            !preValidationBottomScroll.isAtBottom) {
          failures.add(
            'Step 3 failed at viewport 1440x400: scrolling to the bottom before '
            'saving should move the Create issue form to its final extent, but '
            '${preValidationBottomScroll.describe()} was observed.',
          );
        }

        if (!saveVisibleBeforeValidation || !cancelVisibleBeforeValidation) {
          failures.add(
            'Step 3 failed at viewport 1440x400: the user should be able to '
            'reach both action buttons before submitting, but '
            'Save=${saveVisibleBeforeValidation ? 'visible' : 'missing'} and '
            'Cancel=${cancelVisibleBeforeValidation ? 'visible' : 'missing'}. '
            'Visible Create issue texts: ${screen.visibleTexts().join(' | ')}.',
          );
        }

        await screen.submitCreateIssue();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        final postValidationExceptions = _drainFrameworkExceptions(tester);
        if (postValidationExceptions.isNotEmpty) {
          failures.add(
            'Step 6 failed at viewport 1440x400: triggering validation on the '
            'empty Create issue form surfaced framework exceptions instead of '
            'keeping the surface scrollable.\nExceptions:\n'
            '${postValidationExceptions.join('\n---\n')}',
          );
        }

        final postValidationScroll = screen.observeVerticalScroll();
        if (postValidationScroll.maxScrollExtent <=
            initialScroll.maxScrollExtent + 0.5) {
          failures.add(
            'Step 5 failed at viewport 1440x400: the scrollable Create issue '
            'body did not grow after inline validation text was injected. '
            'Before validation: ${initialScroll.describe()}. After validation: '
            '${postValidationScroll.describe()}.',
          );
        }

        await screen.scrollToTop();
        final topScrollAfterValidation = screen.observeVerticalScroll();
        final validationVisible = screen.isTextVisibleInViewport(
          summaryValidationMessage,
        );
        final descriptionRectAfter = screen.observeLabeledTextFieldRect(
          'Description',
        );

        if (topScrollAfterValidation.isScrolled) {
          failures.add(
            'Step 5 failed at viewport 1440x400: returning to the top of the '
            'Create issue form after validation did not reset the scroll '
            'position. Observed scroll state: '
            '${topScrollAfterValidation.describe()}.',
          );
        }

        if (!validationVisible) {
          failures.add(
            'Step 4 failed at viewport 1440x400: submitting an empty Summary '
            'should render the visible inline validation message '
            '"$summaryValidationMessage", but it was not found in the Create '
            'issue viewport. Visible Create issue texts: '
            '${screen.visibleTexts().join(' | ')}.',
          );
        }

        if (descriptionRectBefore != null && descriptionRectAfter == null) {
          failures.add(
            'Step 5 failed at viewport 1440x400: the Description field became '
            'unreachable after validation was shown.',
          );
        } else if (descriptionRectBefore != null &&
            descriptionRectAfter != null &&
            descriptionRectAfter.top <= descriptionRectBefore.top + 0.5) {
          failures.add(
            'Step 5 failed at viewport 1440x400: the Description field did not '
            'shift down after the summary validation text appeared, so the extra '
            'error height was not reflected in the visible layout. Before: '
            '${_describeRect(descriptionRectBefore)}. After: '
            '${_describeRect(descriptionRectAfter)}.',
          );
        }

        await screen.scrollToBottom();
        final bottomScrollAfterValidation = screen.observeVerticalScroll();
        final saveVisibleAfterValidation = screen.isTextVisibleInViewport(
          'Save',
        );
        final cancelVisibleAfterValidation = screen.isTextVisibleInViewport(
          'Cancel',
        );
        final saveRect = screen.observeControlRect('Save');
        final cancelRect = screen.observeControlRect('Cancel');

        if (!bottomScrollAfterValidation.isScrolled ||
            !bottomScrollAfterValidation.isAtBottom) {
          failures.add(
            'Step 5 failed at viewport 1440x400: scrolling through the expanded '
            'Create issue form should still reach the final extent after '
            'validation, but ${bottomScrollAfterValidation.describe()} was '
            'observed.',
          );
        }

        if (!saveVisibleAfterValidation || !cancelVisibleAfterValidation) {
          failures.add(
            'Step 7 failed at viewport 1440x400: after validation increased the '
            'content height, the bottom action buttons should remain visible, '
            'but Save=${saveVisibleAfterValidation ? 'visible' : 'missing'} and '
            'Cancel=${cancelVisibleAfterValidation ? 'visible' : 'missing'}. '
            'Visible Create issue texts: ${screen.visibleTexts().join(' | ')}. '
            'Scroll state: ${bottomScrollAfterValidation.describe()}.',
          );
        }

        final saveVisibilityFailure = _controlVisibilityFailure(
          label: 'Save',
          rect: saveRect,
          viewportHeight: viewportHeight,
        );
        if (saveVisibilityFailure != null) {
          failures.add('Step 7 failed: $saveVisibilityFailure');
        }

        final cancelVisibilityFailure = _controlVisibilityFailure(
          label: 'Cancel',
          rect: cancelRect,
          viewportHeight: viewportHeight,
        );
        if (cancelVisibilityFailure != null) {
          failures.add('Step 7 failed: $cancelVisibilityFailure');
        }

        await screen.submitCreateIssue();
        await screen.waitWithoutInteraction(const Duration(milliseconds: 300));

        final repeatedSubmitExceptions = _drainFrameworkExceptions(tester);
        if (repeatedSubmitExceptions.isNotEmpty) {
          failures.add(
            'Step 7 failed at viewport 1440x400: the visible Save action was '
            'not safely interactable after validation because re-submitting from '
            'the bottom surfaced framework exceptions.\nExceptions:\n'
            '${repeatedSubmitExceptions.join('\n---\n')}',
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

String? _controlVisibilityFailure({
  required String label,
  required Rect? rect,
  required double viewportHeight,
}) {
  if (rect == null) {
    return 'no visible "$label" control was rendered at the bottom of the '
        'Create issue surface.';
  }
  if (rect.top < -0.5 || rect.bottom > viewportHeight + 0.5) {
    return 'the "$label" control was not fully visible inside the 1440x400 '
        'viewport. Observed rect: ${_describeRect(rect)}.';
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

String _describeRect(Rect rect) {
  return '(${rect.left.toStringAsFixed(1)}, ${rect.top.toStringAsFixed(1)}) '
      '${rect.width.toStringAsFixed(1)}x${rect.height.toStringAsFixed(1)}';
}
