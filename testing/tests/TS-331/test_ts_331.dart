import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-331 collaboration tab strip exposes exactly one keyboard-focusable node per tab',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];

      const issueKey = 'TRACK-12';
      const issueSummary = 'Implement Git sync service';
      const expectedTabOrder = <String>[
        'Detail',
        'Comments',
        'Attachments',
        'History',
      ];

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);
        await screen.openSearch();
        await screen.selectIssue(issueKey, issueSummary);

        expect(
          screen.showsIssueDetail(issueKey),
          isTrue,
          reason:
              'The test fixture must open the TRACK-12 issue detail before the collaboration tab strip can be checked.',
        );

        final visibleTexts = screen.visibleTextsWithinIssueDetail(issueKey);
        for (final requiredText in expectedTabOrder) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Human-visible collaboration tab text "$requiredText" was not rendered in issue detail. '
              'Visible issue-detail text: ${visibleTexts.join(' | ')}.',
            );
          }
        }

        final traversal = screen.semanticsLabelsInIssueDetailTraversal(
          issueKey,
        );
        final traversalFailure = _logicalTabOrderFailure(
          traversal,
          expectedOrder: expectedTabOrder,
        );
        if (traversalFailure != null) {
          failures.add(
            '$traversalFailure Observed accessibility traversal: ${traversal.join(' -> ')}.',
          );
        }

        final buttonLabels = screen.buttonLabelsInIssueDetail(issueKey);
        for (final tabLabel in expectedTabOrder) {
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

        final keyboardTabOrder = await screen
            .collectForwardCollaborationTabFocusOrder(issueKey);
        if (!_listsEqual(keyboardTabOrder, expectedTabOrder)) {
          failures.add(
            'Keyboard Tab traversal reached collaboration tabs as ${keyboardTabOrder.join(' -> ')} instead of '
            '${expectedTabOrder.join(' -> ')}. '
            'Observed semantics traversal: ${traversal.join(' -> ')}. '
            'Observed button labels: ${buttonLabels.join(' | ')}.',
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

String? _logicalTabOrderFailure(
  List<String> traversal, {
  required List<String> expectedOrder,
}) {
  var previousIndex = -1;
  for (final label in expectedOrder) {
    final index = traversal.indexOf(label);
    if (index == -1) {
      return 'The collaboration accessibility traversal did not expose "$label" as a keyboard or screen-reader target.';
    }
    if (index <= previousIndex) {
      return 'The collaboration accessibility traversal did not keep the tabs in logical keyboard order.';
    }
    previousIndex = index;
  }
  return null;
}

bool _listsEqual(List<String> actual, List<String> expected) {
  if (actual.length != expected.length) {
    return false;
  }
  for (var index = 0; index < actual.length; index += 1) {
    if (actual[index] != expected[index]) {
      return false;
    }
  }
  return true;
}
