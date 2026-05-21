import 'dart:io' show File;
import 'dart:typed_data';
import 'dart:ui' show Rect, Size;

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/issue_edit_accessibility_robot.dart';
import '../../core/interfaces/issue_edit_accessibility_screen.dart';
import '../../core/utils/local_trackstate_fixture.dart';
import '../../fixtures/issue_edit_accessibility_screen_fixture.dart';

const _approvedDesktopGoldenPath =
    '../../../test/goldens/edit_issue_desktop.png';
const _approvedDesktopGoldenRepositoryPath =
    'test/goldens/edit_issue_desktop.png';
const _requiredDesktopViewport = Size(1440, 900);

void main() {
  testWidgets(
    'TS-885 Edit issue desktop surface matches the approved golden baseline',
    (tester) async {
      final goldenSize = await tester.runAsync(
        () => _readPngSize(_approvedDesktopGoldenRepositoryPath),
      );
      if (goldenSize == null) {
        throw StateError(
          'Reading $_approvedDesktopGoldenRepositoryPath did not complete.',
        );
      }
      expect(
        goldenSize,
        _requiredDesktopViewport,
        reason:
            'TS-885 requires an approved 1440x900 desktop baseline, but '
            '$_approvedDesktopGoldenRepositoryPath is currently '
            '${goldenSize.width.toStringAsFixed(0)}x'
            '${goldenSize.height.toStringAsFixed(0)}. Update the checked-in '
            'golden asset or point this test at the approved 1440x900 '
            'baseline before treating the pixel comparison as a product '
            'regression signal.',
      );

      final semantics = tester.ensureSemantics();
      final robot = IssueEditAccessibilityRobot(tester);
      IssueEditAccessibilityScreenHandle? screen;

      try {
        screen = await launchIssueEditAccessibilityFixture(tester);
        await _resizeViewport(tester, _requiredDesktopViewport);

        for (final text in const [
          'Edit issue',
          'Current status',
          'Status',
          'Summary',
          'Description',
          'Priority',
          'Assignee',
          'Labels',
          'Components',
          'Fix versions',
          'Epic',
          'Save',
          'Cancel',
        ]) {
          expect(
            screen.showsText(text),
            isTrue,
            reason:
                'Step 2 failed: opening Edit issue did not keep the visible '
                '"$text" text on the desktop side-sheet. Visible texts: '
                '${_formatSnapshot(screen.visibleTexts())}.',
          );
        }

        expect(
          await screen.readLabeledTextFieldValue('Summary'),
          LocalTrackStateFixture.issueSummary,
          reason:
              'Step 1 failed: the seeded issue did not load into Edit issue with '
              'the expected Summary value "${LocalTrackStateFixture.issueSummary}".',
        );
        expect(
          await screen.readLabeledTextFieldValue('Description'),
          LocalTrackStateFixture.originalDescription,
          reason:
              'Human-style verification failed: the visible Description field '
              'did not show the seeded issue text '
              '"${LocalTrackStateFixture.originalDescription}".',
        );

        final layout = _observeLayout(tester, robot);
        expect(
          layout.viewportSize,
          _requiredDesktopViewport,
          reason:
              'Step 3 failed: the Edit issue desktop flow did not render at the '
              'approved 1440x900 viewport. Observed ${layout.describe()}.',
        );
        expect(
          layout.rightInset,
          lessThanOrEqualTo(24),
          reason:
              'Human-style verification failed: the Edit issue side-sheet was '
              'not docked to the right desktop edge. Observed ${layout.describe()}.',
        );
        expect(
          layout.leftInset,
          greaterThan(200),
          reason:
              'Human-style verification failed: the Edit issue surface no longer '
              'left the expected desktop content area visible on the left. '
              'Observed ${layout.describe()}.',
        );
        expect(
          layout.widthFraction,
          inInclusiveRange(0.25, 0.5),
          reason:
              'Human-style verification failed: the Edit issue surface no longer '
              'rendered as a desktop side-sheet proportion. Observed '
              '${layout.describe()}.',
        );

        await expectLater(
          find.byType(TrackStateApp),
          matchesGoldenFile(_approvedDesktopGoldenPath),
          reason:
              'Expected Result failed: the rendered Edit issue desktop surface no '
              'longer matches the approved golden baseline at '
              '$_approvedDesktopGoldenPath.',
        );
      } finally {
        await screen?.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

_EditIssueLayoutObservation _observeLayout(
  WidgetTester tester,
  IssueEditAccessibilityRobot robot,
) {
  robot.expectEditIssueSurfaceVisible();
  final rect = tester.getRect(robot.editIssueSurface.first);
  final viewportSize = Size(
    tester.view.physicalSize.width / tester.view.devicePixelRatio,
    tester.view.physicalSize.height / tester.view.devicePixelRatio,
  );
  return _EditIssueLayoutObservation(
    viewportSize: viewportSize,
    surfaceRect: rect,
  );
}

class _EditIssueLayoutObservation {
  const _EditIssueLayoutObservation({
    required this.viewportSize,
    required this.surfaceRect,
  });

  final Size viewportSize;
  final Rect surfaceRect;

  double get leftInset => surfaceRect.left;
  double get rightInset => viewportSize.width - surfaceRect.right;
  double get widthFraction => surfaceRect.width / viewportSize.width;

  String describe() {
    return 'viewport=${viewportSize.width.toStringAsFixed(0)}x'
        '${viewportSize.height.toStringAsFixed(0)}, '
        'rect=(${surfaceRect.left.toStringAsFixed(1)}, '
        '${surfaceRect.top.toStringAsFixed(1)}) '
        '${surfaceRect.width.toStringAsFixed(1)}x'
        '${surfaceRect.height.toStringAsFixed(1)}, '
        'insets=left ${leftInset.toStringAsFixed(1)}, '
        'right ${rightInset.toStringAsFixed(1)}, '
        'width=${(widthFraction * 100).toStringAsFixed(1)}%';
  }
}

Future<void> _resizeViewport(WidgetTester tester, Size size) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
}

String _formatSnapshot(List<String> values, {int limit = 20}) {
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

Future<Size> _readPngSize(String path) async {
  final bytes = await File(path).readAsBytes();
  if (bytes.length < 24) {
    throw StateError(
      'PNG file "$path" is too short to contain an IHDR header.',
    );
  }

  final header = bytes.sublist(0, 8);
  const pngSignature = <int>[137, 80, 78, 71, 13, 10, 26, 10];
  for (var index = 0; index < pngSignature.length; index++) {
    if (header[index] != pngSignature[index]) {
      throw StateError('File "$path" is not a valid PNG image.');
    }
  }

  final chunkType = String.fromCharCodes(bytes.sublist(12, 16));
  if (chunkType != 'IHDR') {
    throw StateError('PNG file "$path" does not start with an IHDR chunk.');
  }

  final byteData = bytes.buffer.asByteData(
    bytes.offsetInBytes,
    bytes.lengthInBytes,
  );
  final width = byteData.getUint32(16);
  final height = byteData.getUint32(20);
  return Size(width.toDouble(), height.toDouble());
}
