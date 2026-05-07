import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../core/fakes/read_only_trackstate_repository.dart';
import '../../frameworks/flutter/widget_test_driver.dart';
import '../pages/issue_detail_page.dart';

class ReadOnlyIssueDetailScreen {
  ReadOnlyIssueDetailScreen._(this.page, this._tester);

  final IssueDetailPage page;
  final WidgetTester _tester;

  static Future<ReadOnlyIssueDetailScreen> launch(WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
    });

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    final driver = WidgetTestDriver(tester);
    await driver.pumpApp(
      TrackStateApp(repository: ReadOnlyTrackStateRepository()),
    );

    return ReadOnlyIssueDetailScreen._(IssueDetailPage(driver), tester);
  }

  void dispose() {
    _tester.view.resetPhysicalSize();
    _tester.view.resetDevicePixelRatio();
  }
}
