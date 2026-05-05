import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  goldenFileComparator = _TolerantGoldenFileComparator(
    Uri.parse('test/trackstate_golden_test.dart'),
    precisionTolerance: 0.04,
  );

  testWidgets('dashboard light desktop golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const TrackStateApp(repository: DemoTrackStateRepository()),
    );
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/dashboard_light_desktop.png'),
    );
  });

  testWidgets('dashboard dark desktop golden', (tester) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const TrackStateApp(repository: DemoTrackStateRepository()),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel('Dark theme'));
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/dashboard_dark_desktop.png'),
    );
  });

  testWidgets('mobile board golden', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const TrackStateApp(repository: DemoTrackStateRepository()),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Board').first);
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(TrackStateApp),
      matchesGoldenFile('goldens/mobile_board.png'),
    );
  });
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
