import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/models/issue_detail_icon_observation.dart';
import '../../core/models/issue_detail_row_style_observation.dart';
import '../../core/models/issue_detail_text_contrast_observation.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-312 collaboration tabs preserve accessible focus order and collaboration-row contrast',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];

      const issueKey = 'TRACK-12';
      const issueSummary = 'Implement Git sync service';
      const attachmentName = 'sync-sequence.svg';
      const attachmentMetadata = 'ana · 2026-05-05T00:08:00Z';
      const historySummary = 'Updated description on TRACK-12';
      const historyMetadata = 'ana · 2026-05-05T00:10:00Z';

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);
        await screen.openSearch();
        await screen.selectIssue(issueKey, issueSummary);

        expect(
          screen.showsIssueDetail(issueKey),
          isTrue,
          reason:
              'The test fixture must open the TRACK-12 issue detail before collaboration accessibility can be checked.',
        );

        final visibleTexts = screen.visibleTextsWithinIssueDetail(issueKey);
        for (final requiredText in [
          issueKey,
          issueSummary,
          'Details',
          'Comments',
          'Attachments',
          'History',
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Human-visible collaboration UI text "$requiredText" was not rendered in issue detail. '
              'Visible issue-detail text: ${visibleTexts.join(' | ')}.',
            );
          }
        }

        final traversal = screen.semanticsLabelsInIssueDetailTraversal(
          issueKey,
        );
        final buttonLabels = screen.buttonLabelsInIssueDetail(issueKey);
        final tabOrderFailure = _logicalTabOrderFailure(
          traversal,
          expectedOrder: const ['Detail', 'Comments', 'Attachments', 'History'],
        );
        if (tabOrderFailure != null) {
          failures.add(
            '$tabOrderFailure Observed accessibility traversal: ${traversal.join(' -> ')}.',
          );
        }

        final detailTabCount = buttonLabels
            .where((candidate) => candidate == 'Detail')
            .length;
        if (detailTabCount != 1) {
          failures.add(
            'The collaboration tab strip must expose exactly one keyboard-focusable "Detail" tab, '
            'but found $detailTabCount. Observed button labels: ${buttonLabels.join(' | ')}.',
          );
        }

        for (final tabLabel in const ['Comments', 'Attachments', 'History']) {
          final count = buttonLabels
              .where((candidate) => candidate == tabLabel)
              .length;
          if (count != 1) {
            failures.add(
              'The collaboration tab strip must expose exactly one keyboard-focusable "$tabLabel" tab, '
              'but found $count. Observed button labels: ${buttonLabels.join(' | ')}.',
            );
          }
        }

        await screen.selectCollaborationTab(issueKey, 'Attachments');
        final attachmentTexts = screen.visibleTextsWithinIssueDetail(issueKey);
        for (final requiredText in [
          attachmentName,
          attachmentMetadata,
          '5240 B',
        ]) {
          if (!attachmentTexts.contains(requiredText)) {
            failures.add(
              'The Attachments tab did not render "$requiredText" as visible row content. '
              'Visible issue-detail text after opening Attachments: ${attachmentTexts.join(' | ')}.',
            );
          }
        }

        final attachmentTraversal = screen
            .semanticsLabelsInIssueDetailTraversal(issueKey);
        final attachmentTraversalFailure = _tabContentTraversalFailure(
          attachmentTraversal,
          tabLabel: 'Attachments',
          firstContentLabel: attachmentName,
        );
        if (attachmentTraversalFailure != null) {
          failures.add(
            '$attachmentTraversalFailure Observed accessibility traversal after opening Attachments: '
            '${attachmentTraversal.join(' -> ')}.',
          );
        }

        final attachmentRowStyle = screen.observeDecoratedRowStyle(
          issueKey,
          rowAnchorText: attachmentName,
        );
        _verifyRowUsesThemeTokens(
          failures,
          observation: attachmentRowStyle,
          context: 'attachment row',
        );

        final attachmentMetadataContrast = screen
            .observeDecoratedRowTextContrast(
              issueKey,
              rowAnchorText: attachmentName,
              text: attachmentMetadata,
            );
        _verifyTextContrast(
          failures,
          observation: attachmentMetadataContrast,
          context: 'attachment metadata',
        );

        final attachmentIcon = screen.observeDecoratedRowIcon(
          issueKey,
          rowAnchorText: attachmentName,
          semanticLabel: attachmentName,
        );
        _verifyIconAccessibility(
          failures,
          observation: attachmentIcon,
          context: 'attachment icon',
        );

        final attachmentButtons = screen.buttonLabelsInIssueDetail(issueKey);
        final downloadButtons = attachmentButtons
            .where((label) => label.toLowerCase().contains('download'))
            .toList(growable: false);
        if (downloadButtons.isEmpty) {
          failures.add(
            'The Attachments tab did not expose any keyboard-focusable download icon or button with a meaningful semantics label. '
            'Observed button labels after opening Attachments: ${attachmentButtons.join(' | ')}.',
          );
        }

        await screen.selectCollaborationTab(issueKey, 'History');
        final historyTexts = screen.visibleTextsWithinIssueDetail(issueKey);
        for (final requiredText in [
          historySummary,
          historyMetadata,
          'Old description -> Read and write tracker files through GitHub Contents API.',
        ]) {
          if (!historyTexts.contains(requiredText)) {
            failures.add(
              'The History tab did not render "$requiredText" as visible row content. '
              'Visible issue-detail text after opening History: ${historyTexts.join(' | ')}.',
            );
          }
        }

        final historyTraversal = screen.semanticsLabelsInIssueDetailTraversal(
          issueKey,
        );
        final historyTraversalFailure = _tabContentTraversalFailure(
          historyTraversal,
          tabLabel: 'History',
          firstContentLabel: historySummary,
        );
        if (historyTraversalFailure != null) {
          failures.add(
            '$historyTraversalFailure Observed accessibility traversal after opening History: '
            '${historyTraversal.join(' -> ')}.',
          );
        }

        final historyRowStyle = screen.observeDecoratedRowStyle(
          issueKey,
          rowAnchorText: historySummary,
        );
        _verifyRowUsesThemeTokens(
          failures,
          observation: historyRowStyle,
          context: 'history row',
        );

        final historyMetadataContrast = screen.observeDecoratedRowTextContrast(
          issueKey,
          rowAnchorText: historySummary,
          text: historyMetadata,
        );
        _verifyTextContrast(
          failures,
          observation: historyMetadataContrast,
          context: 'history metadata',
        );

        final historyIcon = screen.observeDecoratedRowIcon(
          issueKey,
          rowAnchorText: historySummary,
          semanticLabel: historySummary,
        );
        _verifyIconAccessibility(
          failures,
          observation: historyIcon,
          context: 'history icon',
        );

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

String? _logicalTabOrderFailure(
  List<String> traversal, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = traversal.indexOf(label);
    if (index == -1) {
      return 'The collaboration accessibility traversal did not expose "$label" as a screen-reader target.';
    }
    if (index <= previousIndex) {
      return 'The collaboration accessibility traversal did not keep the tabs in logical keyboard order.';
    }
    previousIndex = index;
  }
  return null;
}

String? _tabContentTraversalFailure(
  List<String> traversal, {
  required String tabLabel,
  required String firstContentLabel,
}) {
  final tabIndex = traversal.indexOf(tabLabel);
  final contentIndex = traversal.indexOf(firstContentLabel);
  if (tabIndex == -1 || contentIndex == -1) {
    return 'The $tabLabel tab traversal did not expose both the tab trigger and its first collaboration row content.';
  }
  if (contentIndex <= tabIndex) {
    return 'The $tabLabel collaboration row content appeared before its tab trigger in accessibility traversal order.';
  }
  return null;
}

void _verifyRowUsesThemeTokens(
  List<String> failures, {
  required IssueDetailRowStyleObservation observation,
  required String context,
}) {
  if (!observation.usesExpectedTokens) {
    failures.add(
      'The $context did not follow the neutral collaboration surface tokens. '
      'Observed ${observation.describe()}.',
    );
  }
}

void _verifyTextContrast(
  List<String> failures, {
  required IssueDetailTextContrastObservation observation,
  required String context,
}) {
  if (observation.contrastRatio < 4.5) {
    failures.add(
      'The visible $context contrast was ${observation.describe()}, below the required WCAG AA 4.5:1 threshold.',
    );
  }
}

void _verifyIconAccessibility(
  List<String> failures, {
  required IssueDetailIconObservation observation,
  required String context,
}) {
  if (!observation.usesExpectedOutlineStyle) {
    failures.add(
      'The $context did not follow the expected outline-icon theme tokens. '
      'Observed ${observation.describe()}.',
    );
  }
  if (observation.contrastRatio < 3.0) {
    failures.add(
      'The visible $context contrast was ${observation.describe()}, below the required WCAG AA 3.0:1 threshold for non-text icons.',
    );
  }
}
