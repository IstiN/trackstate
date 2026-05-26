import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/models/issue_detail_text_contrast_observation.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-393 comment composer placeholder contrast stays accessible in the Comments tab',
    (tester) async {
      final semantics = tester.ensureSemantics();
      IssueDetailAccessibilityScreenHandle? screen;

      const issueKey = 'TRACK-12';
      const issueSummary = 'Implement Git sync service';
      const draftComment =
          'QA draft comment for placeholder contrast verification.';

      try {
        screen = await launchIssueDetailAccessibilityFixture(tester);
        final failures = <String>[];

        await screen.openSearch();
        await screen.selectIssue(issueKey, issueSummary);

        expect(
          screen.showsIssueDetail(issueKey),
          isTrue,
          reason:
              'TS-393 must open the seeded issue detail before the Comments tab can be verified.',
        );

        await screen.selectCollaborationTab(issueKey, 'Comments');

        final visibleTexts = screen.visibleTextsWithinIssueDetail(issueKey);
        final semanticsLabels = screen.semanticsLabelsInIssueDetail(issueKey);
        for (final requiredText in const [
          issueKey,
          issueSummary,
          'Comments',
          'Post comment',
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Step 1 failed: the Comments tab did not render the visible "$requiredText" text. '
              'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        if (!semanticsLabels.contains('Comments')) {
          failures.add(
            'Step 1 failed: the Comments tab did not expose the comment composer semantics label "Comments". '
            'Visible semantics labels: ${_formatSnapshot(semanticsLabels)}.',
          );
        }

        final placeholder = screen.commentComposerPlaceholderText(issueKey);
        if (placeholder == null) {
          failures.add(
            'Step 1 failed: the visible comment composer did not render any placeholder hint text. '
            'Observed comment field label: "Comments". Visible issue-detail text: ${_formatSnapshot(visibleTexts)}. '
            'Visible semantics labels: ${_formatSnapshot(semanticsLabels)}.',
          );
        }

        IssueDetailTextContrastObservation? placeholderObservation;
        if (placeholder != null) {
          placeholderObservation = screen
              .observeCommentComposerPlaceholderContrast(issueKey);
          if (placeholderObservation.contrastRatio < 3.0) {
            failures.add(
              'Step 2 failed: the comment composer placeholder contrast was ${placeholderObservation.describe()}, '
              'below the required 3.0:1 threshold for placeholder text.',
            );
          }
        }

        await screen.enterCommentComposerText(issueKey, draftComment);
        final enteredValue = screen.readCommentComposerText(issueKey);
        if (enteredValue != draftComment) {
          failures.add(
            'Step 2 failed: the comment composer did not keep the exact draft text the user entered. '
            'Observed value: ${enteredValue == null ? '<missing>' : '"$enteredValue"'}.',
          );
        }

        final enteredObservation = screen
            .observeCommentComposerEnteredTextContrast(
              issueKey,
              text: draftComment,
            );
        if (placeholderObservation != null &&
            enteredObservation.foregroundHex ==
                placeholderObservation.foregroundHex) {
          failures.add(
            'Step 2 failed: the placeholder and entered comment text both rendered with ${enteredObservation.foregroundHex}, '
            'so the placeholder was not visually distinct from typed content.',
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

String _formatSnapshot(List<String> values, {int limit = 24}) {
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
