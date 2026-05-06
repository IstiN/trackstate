import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

class TrackStateTestHarness {
  TrackStateTestHarness._();

  static Future<void> pumpApp(
    WidgetTester tester, {
    TrackStateRepository repository = const DemoTrackStateRepository(),
    Size size = const Size(1440, 960),
  }) async {
    SharedPreferences.setMockInitialValues({});
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;

    await tester.pumpWidget(TrackStateApp(repository: repository));
    await tester.pumpAndSettle();
  }

  static void resetView(WidgetTester tester) {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  static Finder scrollableBody() => find.byType(SingleChildScrollView).first;
}
