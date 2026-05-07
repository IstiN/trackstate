import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/pages/issue_detail_page.dart';
import '../../components/screens/read_only_issue_detail_screen.dart';
import '../../core/fakes/read_only_trackstate_repository.dart';
import 'widget_test_driver.dart';

class ReadOnlyIssueDetailWidgetFramework {
  ReadOnlyIssueDetailWidgetFramework(this.tester);

  final WidgetTester tester;

  Future<ReadOnlyIssueDetailScreen> launch() async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
    });

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    final driver = WidgetTestDriver(tester);
    await driver.pumpApp(
      TrackStateApp(repository: ReadOnlyTrackStateRepository()),
    );

    return ReadOnlyIssueDetailScreen(
      page: IssueDetailPage(driver),
      onDispose: () {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      },
    );
  }
}
