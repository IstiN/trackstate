import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../core/models/create_issue_layout_observation.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-345 keeps dense Create issue content within flexible bounds during resize',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      const longSummary =
          'TS345SUMMARYTS345SUMMARYTS345SUMMARYTS345SUMMARYTS345SUMMARY'
          'TS345SUMMARYTS345SUMMARYTS345SUMMARYTS345SUMMARYTS345SUMMARY'
          'TS345SUMMARYTS345SUMMARYTS345SUMMARYTS345SUMMARYTS345SUMMARY';
      const longDescription = '''
Paragraph one verifies that the Create issue description editor keeps dense project context readable while the user narrows the viewport.

Paragraph two confirms the form still exposes the action row and text inputs without clipping or overflow indicators during responsive transitions.

Paragraph three preserves realistic user-authored detail so the widget tree has to wrap content and keep the draft intact across breakpoints.
''';
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
        await screen.populateCreateIssueForm(
          summary: longSummary,
          description: longDescription,
        );

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          longSummary,
          reason:
              'Step 1 failed: the Summary field did not retain the long continuous string after entry.',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          longDescription,
          reason:
              'Step 2 failed: the Description field did not retain the multi-paragraph text after entry.',
        );

        final failures = <String>[];

        for (final viewport in resizePath) {
          await screen.resizeToViewport(
            width: viewport.width,
            height: viewport.height,
          );

          final layout = screen.observeLayout();
          final visibleTexts = screen.visibleTexts();
          final visibleSemantics = screen.visibleSemanticsLabels();
          final exceptions = _drainFrameworkExceptions(tester);

          if (exceptions.isNotEmpty) {
            failures.add(
              'Step 4 failed at viewport '
              '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
              'resizing the populated Create issue form surfaced framework exceptions '
              'instead of keeping the UI intact. Observed layout: ${layout.describe()}. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}. '
              'Visible semantics: ${_formatSnapshot(visibleSemantics)}.\n'
              'Exceptions:\n${exceptions.join('\n---\n')}',
            );
          }

          final summaryValue = await screen.readLabeledTextFieldValue(
            'Summary',
          );
          if (summaryValue != longSummary) {
            failures.add(
              'Step 3 failed at viewport '
              '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
              'the Summary field lost part of the long continuous draft during resize. '
              'Observed value: ${_describeObservedFieldValue(summaryValue)}. '
              'Observed layout: ${layout.describe()}. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}. '
              'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
            );
          }

          final descriptionValue = await screen.readLabeledTextFieldValue(
            'Description',
          );
          if (descriptionValue != longDescription) {
            failures.add(
              'Step 3 failed at viewport '
              '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
              'the Description field lost part of the multi-paragraph draft during resize. '
              'Observed value: ${_describeObservedFieldValue(descriptionValue)}. '
              'Observed layout: ${layout.describe()}. '
              'Visible texts: ${_formatSnapshot(visibleTexts)}. '
              'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
            );
          }

          for (final label in const ['Summary', 'Description']) {
            final fieldRect = screen.observeLabeledTextFieldRect(label);
            if (fieldRect == null) {
              failures.add(
                'Step 4 failed at viewport '
                '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
                'the visible "$label" field was not rendered inside Create issue. '
                'Visible texts: ${_formatSnapshot(visibleTexts)}. '
                'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
              );
              continue;
            }

            final boundaryFailure = _horizontalBoundaryFailure(
              rect: fieldRect,
              layout: layout,
              label: '$label field',
            );
            if (boundaryFailure != null) {
              failures.add(
                'Step 4 failed at viewport '
                '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
                '$boundaryFailure Observed layout: ${layout.describe()}.',
              );
            }
          }

          for (final label in const ['Save', 'Cancel']) {
            if (!screen.showsText(label)) {
              failures.add(
                'Step 4 failed at viewport '
                '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
                'the visible "$label" action disappeared from the Create issue form. '
                'Visible texts: ${_formatSnapshot(visibleTexts)}. '
                'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
              );
              continue;
            }

            final controlRect = screen.observeControlRect(label);
            if (controlRect == null) {
              failures.add(
                'Step 4 failed at viewport '
                '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
                'the "$label" action did not expose a measurable visible boundary inside Create issue. '
                'Visible texts: ${_formatSnapshot(visibleTexts)}. '
                'Visible semantics: ${_formatSnapshot(visibleSemantics)}.',
              );
              continue;
            }

            final boundaryFailure = _horizontalBoundaryFailure(
              rect: controlRect,
              layout: layout,
              label: '$label action',
            );
            if (boundaryFailure != null) {
              failures.add(
                'Step 4 failed at viewport '
                '${viewport.width.toStringAsFixed(0)}x${viewport.height.toStringAsFixed(0)}: '
                '$boundaryFailure Observed layout: ${layout.describe()}.',
              );
            }
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
            'Expected Result failed at 390x844: after resizing the populated Create issue form to a compact viewport, '
            'the surface should remain readable as a near full-screen presentation, '
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

String? _horizontalBoundaryFailure({
  required Rect rect,
  required CreateIssueLayoutObservation layout,
  required String label,
}) {
  const epsilon = 0.5;
  final surfaceRight = layout.surfaceLeft + layout.surfaceWidth;

  if (rect.left < layout.surfaceLeft - epsilon ||
      rect.right > surfaceRight + epsilon) {
    return 'The $label overflowed horizontally beyond the visible Create issue surface. '
        'Observed $label bounds: ${_describeRect(rect)}.';
  }
  if (rect.left < -epsilon || rect.right > layout.viewportWidth + epsilon) {
    return 'The $label overflowed horizontally beyond the visible viewport. '
        'Observed $label bounds: ${_describeRect(rect)}.';
  }
  if (rect.width <= epsilon || rect.height <= epsilon) {
    return 'The $label collapsed to a non-visible size. '
        'Observed $label bounds: ${_describeRect(rect)}.';
  }

  return null;
}

String _describeRect(Rect rect) {
  return 'left=${rect.left.toStringAsFixed(1)}, '
      'top=${rect.top.toStringAsFixed(1)}, '
      'right=${rect.right.toStringAsFixed(1)}, '
      'bottom=${rect.bottom.toStringAsFixed(1)}, '
      'width=${rect.width.toStringAsFixed(1)}, '
      'height=${rect.height.toStringAsFixed(1)}';
}

String _describeObservedFieldValue(String? value) {
  if (value == null) {
    return '<null>';
  }
  if (value.isEmpty) {
    return '<empty string>';
  }
  return value;
}

List<String> _drainFrameworkExceptions(WidgetTester tester) {
  final messages = <String>[];
  Object? exception;
  while ((exception = tester.takeException()) != null) {
    messages.add(exception.toString());
  }
  return messages;
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
