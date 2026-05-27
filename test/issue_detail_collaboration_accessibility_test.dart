import 'package:flutter_test/flutter_test.dart';

import '../testing/core/interfaces/issue_detail_accessibility_screen.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'issue detail collaboration tabs expose single-focus targets, download control, and readable metadata',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);

        await screen.openSearch();
        await screen.selectIssue('TRACK-12', 'Implement Git sync service');

        final traversal = screen.semanticsLabelsInIssueDetailTraversal(
          'TRACK-12',
        );
        expect(
          traversal.indexOf('Detail'),
          greaterThanOrEqualTo(0),
          reason: 'Issue detail should expose a keyboard-focusable Detail tab.',
        );
        expect(
          traversal.indexOf('Comments'),
          greaterThan(traversal.indexOf('Detail')),
          reason: 'Comments should appear after Detail in traversal order.',
        );
        expect(
          traversal.indexOf('Attachments'),
          greaterThan(traversal.indexOf('Comments')),
          reason: 'Attachments should appear after Comments in traversal order.',
        );
        expect(
          traversal.indexOf('History'),
          greaterThan(traversal.indexOf('Attachments')),
          reason: 'History should appear after Attachments in traversal order.',
        );

        final buttonLabels = screen.buttonLabelsInIssueDetail('TRACK-12');
        for (final label in const [
          'Detail',
          'Comments',
          'Attachments',
          'History',
        ]) {
          expect(
            buttonLabels.where((candidate) => candidate == label),
            hasLength(1),
            reason: 'Issue detail should expose exactly one "$label" tab.',
          );
        }

        await screen.selectCollaborationTab('TRACK-12', 'Attachments');
        final attachmentMetadataContrast = screen.observeDecoratedRowTextContrast(
          'TRACK-12',
          rowAnchorText: 'sync-sequence.svg',
          text: 'ana · 2026-05-05T00:08:00Z',
        );
        expect(
          attachmentMetadataContrast.contrastRatio,
          greaterThanOrEqualTo(4.5),
          reason: 'Attachment metadata must meet WCAG AA contrast.',
        );
        expect(
          screen
              .buttonLabelsInIssueDetail('TRACK-12')
              .where((label) => label.toLowerCase().contains('download')),
          isNotEmpty,
          reason:
              'Attachments should expose a keyboard-focusable download control.',
        );

        await screen.selectCollaborationTab('TRACK-12', 'History');
        final historyMetadataContrast = screen.observeDecoratedRowTextContrast(
          'TRACK-12',
          rowAnchorText: 'Updated description on TRACK-12',
          text: 'ana · 2026-05-05T00:10:00Z',
        );
        expect(
          historyMetadataContrast.contrastRatio,
          greaterThanOrEqualTo(4.5),
          reason: 'History metadata must meet WCAG AA contrast.',
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
