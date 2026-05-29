import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';
import '../testing/core/interfaces/issue_detail_accessibility_screen.dart';
import '../testing/core/utils/color_contrast.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

void main() {
  testWidgets(
    'issue detail collaboration metadata uses the readable collaboration token in light theme',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);

        await screen.openSearch();
        await screen.selectIssue('TRACK-12', 'Implement Git sync service');

        await screen.selectCollaborationTab('TRACK-12', 'Comments');
        final commentMetadata = find.text(
          '2026-05-05T00:10:00Z',
          findRichText: true,
        );
        expect(commentMetadata, findsOneWidget);
        _expectReadableCollaborationMetadataStyle(tester, commentMetadata);

        await screen.selectCollaborationTab('TRACK-12', 'History');
        final historyMetadata = find.text(
          'ana · 2026-05-05T00:10:00Z',
          findRichText: true,
        );
        expect(historyMetadata, findsOneWidget);
        _expectReadableCollaborationMetadataStyle(tester, historyMetadata);
      } finally {
        semantics.dispose();
      }
    },
  );
}

void _expectReadableCollaborationMetadataStyle(
  WidgetTester tester,
  Finder finder,
) {
  final style = _textStyle(tester, finder);
  final context = tester.element(finder);
  final theme = Theme.of(context);
  final colors = context.ts;
  final expectedStyle = theme.textTheme.labelSmall?.copyWith(
    color: colors.text,
    fontSize: 12,
    fontWeight: FontWeight.w500,
    height: 1.2,
    letterSpacing: .24,
  );

  expect(expectedStyle, isNotNull);
  expect(
    _matchesTextStyleToken(style, expectedStyle!),
    isTrue,
    reason:
        'Collaboration metadata must use the readable 12px label token instead of the smaller muted labelSmall style.',
  );
  expect(
    contrastRatio(style.color!, colors.surfaceAlt),
    greaterThanOrEqualTo(4.5),
    reason:
        'Collaboration metadata foreground must keep WCAG AA contrast on the issue-detail alternate surface.',
  );
}

TextStyle _textStyle(WidgetTester tester, Finder finder) {
  final widget = tester.widget(finder);
  if (widget is Text) {
    return widget.style!;
  }
  if (widget is RichText) {
    return widget.text.style!;
  }
  throw StateError('Expected Text or RichText for $finder, got ${widget.runtimeType}.');
}

bool _matchesTextStyleToken(TextStyle actual, TextStyle expected) {
  return actual.fontSize == expected.fontSize &&
      actual.fontWeight == expected.fontWeight &&
      actual.height == expected.height &&
      actual.letterSpacing == expected.letterSpacing &&
      actual.fontFamily == expected.fontFamily &&
      actual.color == expected.color;
}
