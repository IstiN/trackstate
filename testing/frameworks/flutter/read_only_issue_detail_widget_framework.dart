import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/read_only_issue_detail_screen_component.dart';
import '../../core/fakes/read_only_trackstate_repository.dart';
import '../../core/interfaces/read_only_issue_detail_harness.dart';
import '../../core/interfaces/read_only_issue_detail_screen.dart';
import 'widget_test_driver.dart';

class ReadOnlyIssueDetailWidgetFramework implements ReadOnlyIssueDetailHarness {
  ReadOnlyIssueDetailWidgetFramework(this.tester);

  final WidgetTester tester;

  @override
  Future<void> launch() async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
    });

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    final driver = WidgetTestDriver(tester);
    await driver.pumpApp(
      TrackStateApp(repository: ReadOnlyTrackStateRepository()),
    );
  }

  @override
  void dispose() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }
}

Future<ReadOnlyIssueDetailScreenHandle> launchReadOnlyIssueDetailWidgetScreen(
  WidgetTester tester,
) {
  return createReadOnlyIssueDetailScreen(
    driver: WidgetTestDriver(tester),
    harness: ReadOnlyIssueDetailWidgetFramework(tester),
  );
}
