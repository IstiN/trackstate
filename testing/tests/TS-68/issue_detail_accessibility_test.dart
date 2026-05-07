import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-68 issue detail exposes accessible semantics labels and logical traversal for rich fields',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];

      const issueKey = 'TRACK-12';
      const issueSummary = 'Implement Git sync service';
      const expectedCommentBody =
          'Use repository indexes for key lookup instead of full-tree scans.';

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);
        await screen.openSearch();
        await screen.selectIssue(issueKey, issueSummary);

        expect(
          screen.showsIssueDetail(issueKey),
          isTrue,
          reason:
              'The test fixture must open the TRACK-12 issue detail before accessibility can be checked.',
        );

        final visibleTexts = screen.visibleTextsWithinIssueDetail(issueKey);
        final semanticsLabels = screen.semanticsLabelsInIssueDetail(issueKey);
        final semanticsTraversal = screen.semanticsLabelsInIssueDetailTraversal(
          issueKey,
        );
        final commentActionLabels = screen.commentActionLabels(issueKey);

        for (final requiredText in [
          issueKey,
          issueSummary,
          'Comments',
          'ana',
          expectedCommentBody,
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Human-visible issue detail text "$requiredText" was not rendered. Visible issue-detail text: ${visibleTexts.join(' | ')}.',
            );
          }
        }

        for (final missingRichField in ['tracker-core', '8', 'web', 'mobile']) {
          if (!visibleTexts.contains(missingRichField)) {
            failures.add(
              'Expected rich issue metadata "$missingRichField" to be visible in the expanded issue detail, but it was absent. Visible issue-detail text: ${visibleTexts.join(' | ')}.',
            );
          }
        }

        final inProgressLabelCount = semanticsLabels
            .where((label) => label == 'In Progress')
            .length;
        if (inProgressLabelCount != 1) {
          failures.add(
            'The issue detail must expose exactly one "In Progress" semantics label, but found $inProgressLabelCount.',
          );
        }

        final componentLabelCount = semanticsLabels
            .where((label) => label == 'tracker-core')
            .length;
        if (componentLabelCount != 1) {
          failures.add(
            'The issue detail must expose exactly one "tracker-core" semantics label, but found $componentLabelCount.',
          );
        }

        if (commentActionLabels.isEmpty) {
          failures.add(
            'No comment action controls were rendered after the Comments heading, so there are no comment-action semantics labels for a screen reader to announce.',
          );
        } else {
          final duplicateLabels = <String>{
            for (final label in commentActionLabels)
              if (commentActionLabels
                      .where((candidate) => candidate == label)
                      .length >
                  1)
                label,
          };
          if (duplicateLabels.isNotEmpty) {
            failures.add(
              'Comment action semantics labels must be unique, but duplicates were observed: ${duplicateLabels.join(', ')}.',
            );
          }
          for (final label in commentActionLabels.toSet()) {
            final exactCount = semanticsLabels
                .where((candidate) => candidate == label)
                .length;
            if (exactCount != 1) {
              failures.add(
                'Comment action "$label" must expose exactly one semantics label, but found $exactCount.',
              );
            }
          }
        }

        final traversalFailure = _logicalTraversalFailure(
          semanticsTraversal,
          issueSummary: issueSummary,
          metadataLabels: const ['In Progress', 'tracker-core', '8', 'web', 'mobile'],
          commentsHeading: 'Comments',
          commentAuthor: 'ana',
          commentBody: expectedCommentBody,
        );
        if (traversalFailure != null) {
          failures.add(
            '$traversalFailure Observed traversal labels: ${semanticsTraversal.join(' -> ')}.',
          );
        }

        final inProgressContrast = screen.observeStatusBadgeContrast(
          issueKey,
          'In Progress',
        );
        if (inProgressContrast.contrastRatio < 4.5) {
          failures.add(
            'The visible In Progress status badge contrast was '
            '${inProgressContrast.contrastRatio.toStringAsFixed(2)}:1 '
            '(${inProgressContrast.describe()}), below the required WCAG AA 4.5:1 threshold.',
          );
        }

        if (failures.isNotEmpty) {
          fail(failures.join('\n'));
        }
      } finally {
        semantics.dispose();
      }
    },
  );
}

String? _logicalTraversalFailure(
  List<String> traversal, {
  required String issueSummary,
  required List<String> metadataLabels,
  required String commentsHeading,
  required String commentAuthor,
  required String commentBody,
}) {
  final summaryIndex = traversal.indexOf(issueSummary);
  final commentsIndex = traversal.indexOf(commentsHeading);
  final authorIndex = traversal.indexOf(commentAuthor);
  final bodyIndex = traversal.indexOf(commentBody);

  if (summaryIndex == -1 ||
      commentsIndex == -1 ||
      authorIndex == -1 ||
      bodyIndex == -1) {
    return 'Issue detail semantics traversal did not expose the expected summary, comments heading, author, and comment body targets in screen-reader order.';
  }

  for (final label in metadataLabels) {
    final index = traversal.indexOf(label);
    if (index == -1 || index <= summaryIndex || index >= commentsIndex) {
      return 'Issue detail semantics traversal did not keep rich metadata between the summary and comments. Missing or misplaced metadata target: $label.';
    }
  }

  if (!(summaryIndex < commentsIndex &&
      commentsIndex < authorIndex &&
      authorIndex < bodyIndex)) {
    return 'Issue detail semantics traversal did not move logically from summary through comments into the comment content.';
  }

  return null;
}
