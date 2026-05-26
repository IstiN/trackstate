import 'package:flutter_test/flutter_test.dart';

import '../testing/core/interfaces/issue_detail_accessibility_screen.dart';
import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'comment composer exposes a readable placeholder distinct from entered text',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);

        await screen.openSearch();
        await screen.selectIssue('TRACK-12', 'Implement Git sync service');
        await screen.selectCollaborationTab('TRACK-12', 'Comments');

        final placeholder = screen.commentComposerPlaceholderText('TRACK-12');
        expect(
          placeholder,
          isNotNull,
          reason:
              'The empty comment composer must render a placeholder hint for accessibility guidance.',
        );

        final placeholderContrast = screen.observeCommentComposerPlaceholderContrast(
          'TRACK-12',
        );
        expect(
          placeholderContrast.contrastRatio,
          greaterThanOrEqualTo(3.0),
          reason:
              'Placeholder text must keep at least 3:1 contrast against the composer background.',
        );

        await screen.enterCommentComposerText(
          'TRACK-12',
          'Regression coverage for placeholder accessibility.',
        );
        final enteredContrast = screen.observeCommentComposerEnteredTextContrast(
          'TRACK-12',
          text: 'Regression coverage for placeholder accessibility.',
        );
        expect(
          enteredContrast.foregroundHex,
          isNot(placeholderContrast.foregroundHex),
          reason:
              'Placeholder styling must remain visually distinct from entered comment text.',
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
