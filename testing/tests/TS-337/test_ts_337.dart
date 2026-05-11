import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/interfaces/create_issue_accessibility_screen.dart';
import '../../fixtures/create_issue_accessibility_screen_fixture.dart';

void main() {
  goldenFileComparator = _TolerantGoldenFileComparator(
    Uri.parse('testing/tests/TS-337/test_ts_337.dart'),
    precisionTolerance: 0.04,
  );

  testWidgets(
    'TS-337 Create issue desktop layout matches the right-docked golden',
    (tester) async {
      final semantics = tester.ensureSemantics();
      CreateIssueAccessibilityScreenHandle? screen;

      try {
        screen = await launchCreateIssueAccessibilityFixture(tester);

        for (final text in const [
          'Create issue',
          'Issue Type',
          'Summary',
          'Description',
          'Priority',
          'Initial status',
          'Epic',
          'Assignee',
          'Labels',
          'Save',
          'Cancel',
        ]) {
          expect(
            screen.showsText(text),
            isTrue,
            reason:
                'The visible Create issue desktop surface should show "$text". '
                'Visible texts: ${screen.visibleTexts().join(' | ')}.',
          );
        }

        final layout = screen.observeLayout();
        expect(
          layout.viewportWidth,
          1440,
          reason: 'TS-337 validates the desktop golden at a 1440px-wide viewport.',
        );
        expect(
          layout.viewportHeight,
          960,
          reason: 'TS-337 validates the desktop golden at a 960px-tall viewport.',
        );
        expect(
          layout.rightInset,
          lessThanOrEqualTo(24),
          reason:
              'The Create issue surface should remain right-aligned to the desktop edge gutter, '
              'but ${layout.describe()} was rendered.',
        );
        expect(
          layout.widthFraction,
          inInclusiveRange(0.3, 0.5),
          reason:
              'The desktop Create issue surface should stay a side sheet instead of stretching '
              'full-width or collapsing into an inset card. Observed ${layout.describe()}.',
        );

        await expectLater(
          find.byType(TrackStateApp),
          matchesGoldenFile('goldens/create_issue_right_docked_desktop.png'),
        );
      } finally {
        await screen?.dispose();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

class _TolerantGoldenFileComparator extends LocalFileComparator {
  _TolerantGoldenFileComparator(
    super.testFile, {
    required double precisionTolerance,
  }) : assert(
         precisionTolerance >= 0 && precisionTolerance <= 1,
         'precisionTolerance must be between 0 and 1',
       ),
       _precisionTolerance = precisionTolerance;

  final double _precisionTolerance;

  @override
  Future<bool> compare(Uint8List imageBytes, Uri golden) async {
    final result = await GoldenFileComparator.compareLists(
      imageBytes,
      await getGoldenBytes(golden),
    );
    final passed = result.passed || result.diffPercent <= _precisionTolerance;
    if (passed) {
      result.dispose();
      return true;
    }

    final error = await generateFailureOutput(result, golden, basedir);
    result.dispose();
    throw FlutterError(error);
  }
}
