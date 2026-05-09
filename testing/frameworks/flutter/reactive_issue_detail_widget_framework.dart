import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/reactive_issue_detail_screen_component.dart';
import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/interfaces/reactive_issue_detail_harness.dart';
import '../../core/interfaces/reactive_issue_detail_screen.dart';
import 'widget_test_driver.dart';

class ReactiveIssueDetailWidgetFramework implements ReactiveIssueDetailHarness {
  ReactiveIssueDetailWidgetFramework(this.tester)
    : repository = ReactiveIssueDetailTrackStateRepository();

  final WidgetTester tester;
  final ReactiveIssueDetailTrackStateRepository repository;

  @override
  Future<void> launch() async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
    });

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    final driver = WidgetTestDriver(tester);
    await driver.pumpApp(TrackStateApp(repository: repository));
  }

  @override
  Future<void> synchronizeSessionToReadOnly() async {
    repository.synchronizeSessionToReadOnly();
    await tester.pump();
    await tester.pumpAndSettle();
  }

  @override
  void dispose() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }
}

Future<ReactiveIssueDetailScreenHandle> launchReactiveIssueDetailWidgetScreen(
  WidgetTester tester,
) {
  return createReactiveIssueDetailScreen(
    driver: WidgetTestDriver(tester),
    harness: ReactiveIssueDetailWidgetFramework(tester),
  );
}
