import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../testing/fixtures/issue_detail_accessibility_screen_fixture.dart';
import '../testing/core/interfaces/issue_detail_accessibility_screen.dart';
import '../testing/core/utils/color_contrast.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';

void main() {
  testWidgets(
    'issue detail collaboration metadata uses the readable collaboration token in both themes',
    (tester) async {
      final semantics = tester.ensureSemantics();

      try {
        final IssueDetailAccessibilityScreenHandle screen =
            await launchIssueDetailAccessibilityFixture(tester);

        await screen.openSearch();
        await screen.selectIssue('TRACK-12', 'Implement Git sync service');

        await _expectReadableMetadataAcrossCollaborationTabs(tester, screen);

        await tester.tap(find.bySemanticsLabel(RegExp(r'^Dark theme$')).last);
        await tester.pumpAndSettle();

        await _expectReadableMetadataAcrossCollaborationTabs(tester, screen);
      } finally {
        semantics.dispose();
      }
    },
  );
}

Future<void> _expectReadableMetadataAcrossCollaborationTabs(
  WidgetTester tester,
  IssueDetailAccessibilityScreenHandle screen,
) async {
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
}

void _expectReadableCollaborationMetadataStyle(
  WidgetTester tester,
  Finder finder,
) {
  final style = _textStyle(tester, finder);
  final context = tester.element(finder);
  final colors = context.ts;
  final expectedStyle = Theme.of(context).textTheme.labelLarge?.copyWith(
    color: colors.text,
    fontSize: 14,
    fontWeight: FontWeight.w700,
    height: 1.25,
    letterSpacing: 0,
  );

  expect(expectedStyle, isNotNull);
  expect(
    style.fontSize,
    expectedStyle!.fontSize,
    reason: 'Collaboration metadata should use the larger readable metadata size.',
  );
  expect(
    style.fontWeight,
    expectedStyle.fontWeight,
    reason: 'Collaboration metadata should use the heavier readable metadata weight.',
  );
  expect(
    style.height,
    expectedStyle.height,
    reason: 'Collaboration metadata should keep the shared readable line height.',
  );
  expect(
    style.letterSpacing,
    expectedStyle.letterSpacing,
    reason: 'Collaboration metadata should keep the shared readable letter spacing.',
  );
  expect(
    style.color,
    colors.text,
    reason:
        'Collaboration metadata must keep the high-contrast foreground token on the issue-detail alternate surface.',
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
