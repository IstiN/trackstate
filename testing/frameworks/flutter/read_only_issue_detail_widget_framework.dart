import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/read_only_issue_detail_screen_component.dart';
import '../../core/fakes/read_only_trackstate_repository.dart';
import '../../core/interfaces/read_only_issue_detail_harness.dart';
import '../../core/interfaces/read_only_issue_detail_screen.dart';
import 'widget_test_driver.dart';

class ReadOnlyIssueDetailWidgetFramework implements ReadOnlyIssueDetailHarness {
  ReadOnlyIssueDetailWidgetFramework(
    this.tester, {
    required this.repository,
    required this.tokenValue,
  });

  final WidgetTester tester;
  final TrackStateRepository repository;
  final String tokenValue;

  @override
  Future<void> launch() async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': tokenValue,
    });

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    final driver = WidgetTestDriver(tester);
    await driver.pumpApp(TrackStateApp(repository: repository));
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
  return launchIssueDetailWidgetScreen(
    tester,
    repository: ReadOnlyTrackStateRepository(),
    tokenValue: 'read-only-token',
  );
}

Future<ReadOnlyIssueDetailScreenHandle> launchWritableIssueDetailWidgetScreen(
  WidgetTester tester,
) {
  return launchIssueDetailWidgetScreen(
    tester,
    repository: WritableTrackStateRepository(),
    tokenValue: 'write-enabled-token',
  );
}

Future<ReadOnlyIssueDetailScreenHandle> launchIssueDetailWidgetScreen(
  WidgetTester tester, {
  required TrackStateRepository repository,
  required String tokenValue,
}) {
  return createReadOnlyIssueDetailScreen(
    driver: WidgetTestDriver(tester),
    harness: ReadOnlyIssueDetailWidgetFramework(
      tester,
      repository: repository,
      tokenValue: tokenValue,
    ),
  );
}
