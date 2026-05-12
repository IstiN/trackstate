import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/models/issue_detail_icon_observation.dart';
import 'support/ts456_deferred_attachment_error_fixture.dart';

void main() {
  testWidgets(
    'TS-456 deferred attachment error accessibility keeps retry semantics, keyboard reachability, and readable contrast',
    (tester) async {
      final semantics = tester.ensureSemantics();
      IssueDetailAccessibilityScreenHandle? screen;

      try {
        final fixture = await Ts456DeferredAttachmentErrorFixture.create();
        screen = await launchTs456DeferredAttachmentErrorScreen(
          tester,
          fixture: fixture,
        );
        final failures = <String>[];

        await screen.openSearch();
        await screen.selectIssue(
          Ts456DeferredAttachmentErrorFixture.issueKey,
          Ts456DeferredAttachmentErrorFixture.issueSummary,
        );

        expect(
          screen.showsIssueDetail(Ts456DeferredAttachmentErrorFixture.issueKey),
          isTrue,
          reason:
              'TS-456 must open the seeded issue detail before the deferred Attachments error state can be verified.',
        );

        await screen.selectCollaborationTab(
          Ts456DeferredAttachmentErrorFixture.issueKey,
          'Attachments',
        );
        await _waitForVisibleText(
          tester,
          Ts456DeferredAttachmentErrorFixture.issueKey,
          Ts456DeferredAttachmentErrorFixture.deferredErrorMessage,
        );

        if (fixture.attachmentReadAttempts < 1) {
          failures.add(
            'Step 2 failed: opening the Attachments tab did not trigger the deferred attachment hydration read. '
            'Observed read attempts: ${fixture.attachmentReadAttempts}.',
          );
        }

        final visibleTexts = screen.visibleTextsWithinIssueDetail(
          Ts456DeferredAttachmentErrorFixture.issueKey,
        );
        for (final requiredText in const [
          'Attachments',
          'Choose a file to review its size before upload.',
          'Choose attachment',
          'Retry',
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Step 2 failed: the Attachments tab did not render the visible "$requiredText" text in the deferred error state. '
              'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }
        if (!visibleTexts.contains(
          Ts456DeferredAttachmentErrorFixture.deferredErrorMessage,
        )) {
          failures.add(
            'Step 2 failed: the deferred attachment error message was not rendered as visible user-facing text. '
            'Expected visible message: ${Ts456DeferredAttachmentErrorFixture.deferredErrorMessage}. '
            'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
          );
        }

        final buttonLabels = screen.buttonLabelsInIssueDetail(
          Ts456DeferredAttachmentErrorFixture.issueKey,
        );
        final retryCount = buttonLabels
            .where((label) => label == 'Retry')
            .length;
        if (retryCount != 1) {
          failures.add(
            'Step 4 failed: the deferred Attachments error state must expose exactly one "Retry" semantics label, '
            'but found $retryCount. Observed button labels: ${_formatSnapshot(buttonLabels)}.',
          );
        }

        final errorIcon = _observeDeferredErrorIcon(
          screen,
          failures,
          issueKey: Ts456DeferredAttachmentErrorFixture.issueKey,
        );
        if (errorIcon != null && errorIcon.contrastRatio < 3.0) {
          failures.add(
            'Step 5 failed: the deferred Attachments error icon contrast was ${errorIcon.describe()}, '
            'below the required WCAG AA 3.0:1 threshold for non-text icons.',
          );
        }

        final retryTraversalFailure = _orderedSubsequenceFailure(
          buttonLabels,
          expectedOrder: const ['Attachments', 'Choose attachment', 'Retry'],
        );
        if (retryTraversalFailure != null) {
          failures.add(
            'Step 3 failed: the deferred Attachments controls did not stay in logical focus order. '
            '$retryTraversalFailure Observed button order: ${buttonLabels.join(' -> ')}.',
          );
        }

        final focusOrder = await _collectForwardFocusOrder(
          tester,
          candidateLabels: const ['Choose attachment', 'Retry'],
        );
        final retryFocusIndex = _indexOfLabel(focusOrder, 'Retry');
        if (retryFocusIndex == -1) {
          failures.add(
            'Step 3 failed: keyboard Tab navigation did not reach the Retry action in the deferred Attachments error state. '
            'Observed Tab order: ${_formatSnapshot(focusOrder)}.',
          );
        }

        if (retryFocusIndex != -1) {
          final retryAttemptsBeforeActivation = fixture.attachmentReadAttempts;
          await tester.sendKeyEvent(LogicalKeyboardKey.enter);
          await _waitForRetryAttempt(
            tester,
            fixture: fixture,
            previousAttempts: retryAttemptsBeforeActivation,
          );
          if (fixture.attachmentReadAttempts <= retryAttemptsBeforeActivation) {
            failures.add(
              'Step 3 failed: pressing Enter on the focused Retry action did not trigger another deferred attachment load attempt. '
              'Observed read attempts before activation: $retryAttemptsBeforeActivation. '
              'Observed read attempts after activation: ${fixture.attachmentReadAttempts}.',
            );
          }
        }

        final titleContrast = screen.observeDecoratedRowTextContrast(
          Ts456DeferredAttachmentErrorFixture.issueKey,
          rowAnchorText: 'Retry',
          text: 'Attachments',
        );
        if (titleContrast.contrastRatio < 4.5) {
          failures.add(
            'Step 5 failed: the visible Attachments error title contrast was ${titleContrast.describe()}, '
            'below the required WCAG AA 4.5:1 threshold for normal text.',
          );
        }

        final messageContrast = screen.observeDecoratedRowTextContrast(
          Ts456DeferredAttachmentErrorFixture.issueKey,
          rowAnchorText: 'Retry',
          text: Ts456DeferredAttachmentErrorFixture.deferredErrorMessage,
        );
        if (messageContrast.contrastRatio < 4.5) {
          failures.add(
            'Step 5 failed: the visible deferred attachment error message contrast was ${messageContrast.describe()}, '
            'below the required WCAG AA 4.5:1 threshold for normal text.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<void> _waitForVisibleText(
  WidgetTester tester,
  String issueKey,
  String text,
) async {
  final issueDetail = find.bySemanticsLabel(RegExp('Issue detail $issueKey'));
  final end = DateTime.now().add(const Duration(seconds: 5));
  while (DateTime.now().isBefore(end)) {
    final textFinder = find.descendant(
      of: issueDetail,
      matching: find.text(text, findRichText: true),
    );
    if (textFinder.evaluate().isNotEmpty) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  throw StateError(
    'Timed out waiting for "$text" to render in the issue detail for $issueKey.',
  );
}

Future<List<String>> _collectForwardFocusOrder(
  WidgetTester tester, {
  required List<String> candidateLabels,
}) async {
  FocusManager.instance.primaryFocus?.unfocus();
  await tester.pump();

  final order = <String>[];
  for (var index = 0; index < 16; index += 1) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    final focusedLabel = _focusedCandidateLabel(candidateLabels);
    if (focusedLabel != null && (order.isEmpty || order.last != focusedLabel)) {
      order.add(focusedLabel);
    }
    if (_indexOfLabel(order, 'Retry') != -1) {
      break;
    }
  }
  return order;
}

String? _focusedCandidateLabel(List<String> candidateLabels) {
  for (final label in candidateLabels) {
    final focused = find.semantics.byPredicate(
      (node) =>
          node.getSemanticsData().flagsCollection.isFocused &&
          _matchesTraversalLabel(_normalizeLabel(node.label), label),
      describeMatch: (_) => 'focused semantics labeled $label',
    );
    if (focused.evaluate().isNotEmpty) {
      return label;
    }
  }
  return null;
}

Future<void> _waitForRetryAttempt(
  WidgetTester tester, {
  required Ts456DeferredAttachmentErrorFixture fixture,
  required int previousAttempts,
}) async {
  final end = DateTime.now().add(const Duration(seconds: 5));
  while (DateTime.now().isBefore(end)) {
    if (fixture.attachmentReadAttempts > previousAttempts) {
      await tester.pumpAndSettle();
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
}

IssueDetailIconObservation? _observeDeferredErrorIcon(
  IssueDetailAccessibilityScreenHandle screen,
  List<String> failures, {
  required String issueKey,
}) {
  try {
    return screen.observeDecoratedRowIcon(
      issueKey,
      rowAnchorText: 'Retry',
      semanticLabel:
          Ts456DeferredAttachmentErrorFixture.deferredErrorIconSemanticLabel,
    );
  } on StateError {
    failures.add(
      'Step 4 failed: the deferred Attachments error state must expose a separate error icon with semantics label '
      '"${Ts456DeferredAttachmentErrorFixture.deferredErrorIconSemanticLabel}" so screen-reader users can identify the error treatment. '
      'Observed result: no matching icon was rendered in the deferred error card.',
    );
    return null;
  }
}

String? _orderedSubsequenceFailure(
  List<String> observed, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = _indexOfLabel(observed, label);
    if (index == -1) {
      return 'The accessibility order did not expose "$label" as a reachable target.';
    }
    if (index <= previousIndex) {
      return 'The accessibility order did not keep the deferred Attachments actions in logical top-to-bottom order.';
    }
    previousIndex = index;
  }
  return null;
}

int _indexOfLabel(List<String> observed, String label) {
  for (var index = 0; index < observed.length; index += 1) {
    if (_matchesTraversalLabel(observed[index], label)) {
      return index;
    }
  }
  return -1;
}

bool _matchesTraversalLabel(String observed, String label) =>
    observed == label || observed.startsWith('$label ');

String _normalizeLabel(String? label) =>
    (label ?? '').replaceAll(RegExp(r'\s+'), ' ').trim();

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
