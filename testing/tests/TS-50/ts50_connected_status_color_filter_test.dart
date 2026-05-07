import 'dart:typed_data';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_blindness_filters.dart';

void main() {
  goldenFileComparator = _TolerantGoldenFileComparator(
    Uri.parse(
      'testing/tests/TS-50/ts50_connected_status_color_filter_test.dart',
    ),
    precisionTolerance: 0.02,
  );

  testWidgets(
    'TS-50 connected status remains distinguishable when color cues are removed',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final filteredAppBoundaryKey = GlobalKey();

      try {
        for (final scenario in <({String name, ColorFilter filter})>[
          (name: 'grayscale', filter: ColorBlindnessFilters.grayscale()),
          (name: 'protanopia', filter: ColorBlindnessFilters.protanopia()),
        ]) {
          await robot.pumpApp(
            repository: const DemoTrackStateRepository(),
            sharedPreferences: const {
              'trackstate.githubToken.trackstate.trackstate': 'stored-token',
            },
            appWrapper: (child) => RepaintBoundary(
              key: filteredAppBoundaryKey,
              child: ColorFiltered(colorFilter: scenario.filter, child: child),
            ),
          );
          await robot.openSettings();

          expect(
            robot.connectedControl,
            findsOneWidget,
            reason:
                'The Settings provider control should still render the visible "Connected" label with the ${scenario.name} filter applied.',
          );
          await expectLater(
            find.byKey(filteredAppBoundaryKey),
            matchesGoldenFile(
              'goldens/settings_connected_${scenario.name}.png',
            ),
          );
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
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
