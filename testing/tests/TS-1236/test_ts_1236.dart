import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../core/models/issue_detail_text_contrast_observation.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-1236 empty comment composer shows the exact Add a comment placeholder',
    (tester) async {
      final semantics = tester.ensureSemantics();
      IssueDetailAccessibilityScreenHandle? screen;

      const issueKey = 'TRACK-12';
      const issueSummary = 'Implement Git sync service';
      const expectedPlaceholder = 'Add a comment...';

      try {
        screen = await launchIssueDetailAccessibilityFixture(tester);

        await screen.openSearch();
        await screen.selectIssue(issueKey, issueSummary);

        expect(
          screen.showsIssueDetail(issueKey),
          isTrue,
          reason:
              'TS-1236 must open the seeded issue detail before the empty comment composer can be inspected.',
        );

        await screen.selectCollaborationTab(issueKey, 'Comments');

        final failures = <String>[];
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
              'Step 2 failed: the Comments tab did not render the visible "$requiredText" text. '
              'Visible issue-detail text: ${_formatSnapshot(visibleTexts)}.',
            );
          }
        }

        if (!semanticsLabels.contains('Comments')) {
          failures.add(
            'Step 2 failed: the empty comment composer did not expose the expected "Comments" semantics label. '
            'Visible semantics labels: ${_formatSnapshot(semanticsLabels)}.',
          );
        }

        final placeholder = screen.commentComposerPlaceholderText(issueKey);
        if (placeholder == null) {
          failures.add(
            'Step 3 failed: the empty comment composer did not render any placeholder hint text. '
            'Observed field label: "Comments". Visible issue-detail text: ${_formatSnapshot(visibleTexts)}. '
            'Visible semantics labels: ${_formatSnapshot(semanticsLabels)}.',
          );
        } else if (placeholder != expectedPlaceholder) {
          failures.add(
            'Step 3 failed: the empty comment composer rendered "$placeholder" instead of the expected '
            '"$expectedPlaceholder" placeholder text.',
          );
        }

        IssueDetailTextContrastObservation? placeholderObservation;
        if (placeholder != null) {
          placeholderObservation = screen
              .observeCommentComposerPlaceholderContrast(issueKey);
          if (placeholderObservation.text != expectedPlaceholder) {
            failures.add(
              'Step 3 failed: the visible placeholder painted in the input was '
              '"${placeholderObservation.text}" instead of "$expectedPlaceholder".',
            );
          }
        }

        if (screen.readCommentComposerText(issueKey)?.isNotEmpty ?? false) {
          failures.add(
            'Step 3 failed: the comment composer was not empty before inspection. '
            'Observed value: "${screen.readCommentComposerText(issueKey)}".',
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
