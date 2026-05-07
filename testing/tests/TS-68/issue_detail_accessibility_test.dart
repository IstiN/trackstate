import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/issue_detail_accessibility_robot.dart';
import '../../core/utils/color_contrast.dart';
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
        final IssueDetailAccessibilityRobot robot =
            await launchIssueDetailAccessibilityFixture(tester);
        await robot.openSearch();
        await robot.openIssue(issueKey, issueSummary);

        expect(
          robot.issueDetail(issueKey),
          findsOneWidget,
          reason:
              'The test fixture must open the TRACK-12 issue detail before accessibility can be checked.',
        );

        final visibleTexts = robot.visibleTextsWithinIssueDetail(issueKey);
        final semanticsTraversal = robot.semanticsLabelsInIssueDetailTraversal(
          issueKey,
        );
        final commentActionLabels = robot.commentActionLabels(issueKey);

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

        final inProgressLabelCount = semanticsTraversal
            .where((label) => label == 'In Progress')
            .length;
        if (inProgressLabelCount != 1) {
          failures.add(
            'The issue detail must expose exactly one "In Progress" semantics label, but found $inProgressLabelCount.',
          );
        }

        final componentLabelCount = semanticsTraversal
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
            final exactCount = semanticsTraversal
                .where((candidate) => candidate == label)
                .length;
            if (exactCount != 1) {
              failures.add(
                'Comment action "$label" must expose exactly one semantics label, but found $exactCount.',
              );
            }
          }
        }

        if (!containsAllInOrder([
          issueSummary,
          'In Progress',
          'Details',
          'Comments',
          'ana',
          expectedCommentBody,
        ]).matches(semanticsTraversal, <dynamic, dynamic>{})) {
          failures.add(
            'Issue detail semantics traversal did not move logically from summary through metadata into comments. Observed traversal labels: ${semanticsTraversal.join(' -> ')}.',
          );
        }

        final inProgressContrast = contrastRatio(
          robot.colors().accent,
          robot.colors().accentSoft,
        );
        if (inProgressContrast < 4.5) {
          failures.add(
            'The visible In Progress status badge contrast was ${inProgressContrast.toStringAsFixed(2)}:1, below the required WCAG AA 4.5:1 threshold.',
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
