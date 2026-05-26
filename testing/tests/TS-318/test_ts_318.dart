import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/jql_search_accessibility_screen.dart';
import '../../fixtures/jql_search_accessibility_screen_fixture.dart';

void main() {
  testWidgets(
    'TS-318 JQL Search accessibility keeps labels, focus order, and pagination styling aligned with AC5',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final failures = <String>[];

      try {
        final JqlSearchAccessibilityScreenHandle screen =
            await launchJqlSearchAccessibilityFixture(tester);
        await screen.openSearch();

        final visibleTexts = screen.visibleTexts();
        for (final requiredText in const [
          'Showing 6 of 8 issues',
          'Paged issue 1',
          'Paged issue 6',
          'Load more',
        ]) {
          if (!visibleTexts.contains(requiredText)) {
            failures.add(
              'Human-visible JQL Search content "$requiredText" was not rendered. '
              'Visible JQL Search texts: ${visibleTexts.join(' | ')}.',
            );
          }
        }

        final traversal = screen.semanticsTraversal();
        final duplicateInteractiveLabels = <String>[
          'Search issues',
          'Load more issues',
        ].where((label) => screen.countExactSemanticsLabel(label) > 1).toList();
        if (duplicateInteractiveLabels.isNotEmpty) {
          failures.add(
            'Interactive semantics labels must stay unique on JQL Search, but duplicates were observed: '
            '${duplicateInteractiveLabels.join(', ')}. '
            'Observed traversal: ${traversal.join(' -> ')}.',
          );
        }

        for (final requiredLabel in const [
          'Search issues',
          'Load more issues',
        ]) {
          final count = screen.countExactSemanticsLabel(requiredLabel);
          if (count != 1) {
            failures.add(
              'The JQL Search semantics tree must expose exactly one "$requiredLabel" label, but found $count. '
              'Observed traversal: ${traversal.join(' -> ')}.',
            );
          }
        }

        final traversalFailure = _logicalTraversalFailure(traversal);
        if (traversalFailure != null) {
          failures.add(
            '$traversalFailure Observed traversal: ${traversal.join(' -> ')}.',
          );
        }

        final forwardFocusOrder = await screen.collectForwardFocusOrder();
        final expectedForwardFocusOrder = [
          'Search issues',
          for (var index = 1; index <= 6; index += 1)
            'Open TRACK-$index Paged issue $index',
          'Load more issues',
        ];
        if (!_listsEqual(forwardFocusOrder, expectedForwardFocusOrder)) {
          failures.add(
            'Keyboard Tab order on JQL Search was ${forwardFocusOrder.join(' -> ')} instead of '
            '${expectedForwardFocusOrder.join(' -> ')}.',
          );
        }

        final backwardFocusOrder = await screen.collectBackwardFocusOrder();
        final expectedBackwardFocusOrder = [
          'Load more issues',
          for (var index = 6; index >= 1; index -= 1)
            'Open TRACK-$index Paged issue $index',
          'Search issues',
        ];
        if (!_listsEqual(backwardFocusOrder, expectedBackwardFocusOrder)) {
          failures.add(
            'Keyboard Shift+Tab order on JQL Search was ${backwardFocusOrder.join(' -> ')} instead of '
            '${expectedBackwardFocusOrder.join(' -> ')}.',
          );
        }

        final idleObservation = screen.observeLoadMoreButtonIdle();
        if (!idleObservation.usesExpectedBaseTokens) {
          failures.add(
            'The visible Load more button did not render terracotta primary on surface in its idle state. '
            'Observed ${idleObservation.describe()}.',
          );
        }
        if (idleObservation.contrastRatio < 4.5) {
          failures.add(
            'The visible Load more button contrast was ${idleObservation.describe()}, '
            'below the required WCAG AA 4.5:1 threshold.',
          );
        }

        final hoveredObservation = screen.observeLoadMoreButtonHovered();
        if (!hoveredObservation.usesExpectedInteractionTokens) {
          failures.add(
            'The hovered Load more button did not use the expected primary and primarySoft design tokens. '
            'Observed ${hoveredObservation.describe()}.',
          );
        }

        final focusedObservation = screen.observeLoadMoreButtonFocused();
        if (!focusedObservation.usesExpectedInteractionTokens) {
          failures.add(
            'The focused Load more button did not use the expected primary and primarySoft design tokens. '
            'Observed ${focusedObservation.describe()}.',
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

String? _logicalTraversalFailure(List<String> traversal) {
  final searchIndex = _indexOfLabelContaining(traversal, 'Search issues');
  final loadMoreIndex = _indexOfLabelContaining(traversal, 'Load more');
  if (searchIndex == -1 || loadMoreIndex == -1) {
    return 'The JQL Search accessibility traversal did not expose both the search input and the pagination control.';
  }

  if (loadMoreIndex <= searchIndex) {
    return 'The pagination control appeared before the search input in accessibility traversal order.';
  }

  for (var index = 1; index <= 6; index += 1) {
    final issueLabel = 'Open TRACK-$index Paged issue $index';
    final issueIndex = _indexOfLabelContaining(traversal, issueLabel);
    if (issueIndex == -1) {
      return 'The JQL Search accessibility traversal did not expose "$issueLabel" from the paginated result list.';
    }
    if (issueIndex <= searchIndex || issueIndex >= loadMoreIndex) {
      return 'The JQL Search accessibility traversal did not keep the visible result list between the search input and the Load more control.';
    }
    if (index > 1) {
      final previousIndex = _indexOfLabelContaining(
        traversal,
        'Open TRACK-${index - 1} Paged issue ${index - 1}',
      );
      if (issueIndex <= previousIndex) {
        return 'The JQL Search accessibility traversal did not keep visible result rows in top-to-bottom order.';
      }
    }
  }

  return null;
}

int _indexOfLabelContaining(List<String> traversal, String fragment) {
  for (var index = 0; index < traversal.length; index += 1) {
    if (traversal[index].contains(fragment)) {
      return index;
    }
  }
  return -1;
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
