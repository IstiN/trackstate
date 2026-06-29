import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/widgets.dart';

import '../testing/core/interfaces/issue_detail_accessibility_screen.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';
import '../testing/tests/TS-456/support/ts456_deferred_attachment_error_fixture.dart';

void main() {
  testWidgets(
    'attachments deferred error exposes standalone retry semantics and readable styling',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final fixture = await Ts456DeferredAttachmentErrorFixture.create();
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(
              tester,
              repository: fixture.repository,
            );

        await screen.openSearch();
        await screen.selectIssue(
          Ts456DeferredAttachmentErrorFixture.issueKey,
          Ts456DeferredAttachmentErrorFixture.issueSummary,
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

        expect(fixture.attachmentReadAttempts, greaterThan(0));

        final buttonLabels = screen.buttonLabelsInIssueDetail(
          Ts456DeferredAttachmentErrorFixture.issueKey,
        );
        expect(
          buttonLabels.where((label) => label == 'Retry'),
          hasLength(1),
          reason:
              'Deferred attachment errors must expose a standalone Retry button semantics node.',
        );

        final focusOrder = await _collectForwardFocusOrder(
          tester,
          candidateLabels: const ['Choose attachment', 'Retry'],
        );
        expect(
          focusOrder.indexOf('Retry'),
          greaterThan(focusOrder.indexOf('Choose attachment')),
          reason: 'Retry should remain in keyboard order after Choose attachment.',
        );

        final themeTokens = screen.themeTokens(
          Ts456DeferredAttachmentErrorFixture.issueKey,
        );
        expect(
          () => screen.observeDecoratedRowIcon(
            Ts456DeferredAttachmentErrorFixture.issueKey,
            rowAnchorText: 'Retry',
            semanticLabel:
                Ts456DeferredAttachmentErrorFixture
                    .deferredErrorIconSemanticLabel,
          ),
          returnsNormally,
          reason:
              'Deferred attachment errors must expose a dedicated error icon semantics target.',
        );

        final titleContrast = screen.observeDecoratedRowTextContrast(
          Ts456DeferredAttachmentErrorFixture.issueKey,
          rowAnchorText: 'Retry',
          text: 'Attachments',
        );
        expect(titleContrast.foregroundHex, themeTokens.errorHex);
        expect(titleContrast.contrastRatio, greaterThanOrEqualTo(4.5));

        final messageContrast = screen.observeDecoratedRowTextContrast(
          Ts456DeferredAttachmentErrorFixture.issueKey,
          rowAnchorText: 'Retry',
          text: Ts456DeferredAttachmentErrorFixture.deferredErrorMessage,
        );
        expect(messageContrast.foregroundHex, themeTokens.mutedHex);
        expect(messageContrast.contrastRatio, greaterThanOrEqualTo(4.5));
      } finally {
        semantics.dispose();
      }
    },
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
    if (order.contains('Retry')) {
      break;
    }
  }
  return order;
}

String? _focusedCandidateLabel(List<String> candidateLabels) {
  for (final label in candidateLabels) {
    final focused = find.semantics.byPredicate(
      (node) =>
          node.getSemanticsData().hasFlag(SemanticsFlag.isFocused) &&
          _normalizeLabel(node.label) == label,
      describeMatch: (_) => 'focused semantics labeled $label',
    );
    if (focused.evaluate().isNotEmpty) {
      return label;
    }
  }
  return null;
}

String _normalizeLabel(String? label) =>
    (label ?? '').replaceAll(RegExp(r'\s+'), ' ').trim();