import 'package:flutter_test/flutter_test.dart';

import '../testing/core/interfaces/issue_detail_accessibility_screen.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'issue detail collaboration tabs advance to History and expose history summaries as standalone semantics targets',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);

        await screen.openSearch();
        await screen.selectIssue('TRACK-12', 'Implement Git sync service');

        expect(
          await screen.collectForwardCollaborationTabFocusOrder('TRACK-12'),
          const ['Detail', 'Comments', 'Attachments', 'History'],
          reason:
              'Arrow-key traversal should move across the collaboration tabs without stalling on the selected chip.',
        );

        await screen.selectCollaborationTab('TRACK-12', 'History');
        final traversal = screen.semanticsLabelsInIssueDetailTraversal(
          'TRACK-12',
        );
        final historyIndex = traversal.indexOf('History');
        final summaryIndex = traversal.indexOf(
          'Updated description on TRACK-12',
        );

        expect(
          summaryIndex,
          greaterThan(historyIndex),
          reason:
              'The first history row summary should be exposed as its own semantics target after the History tab.',
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
