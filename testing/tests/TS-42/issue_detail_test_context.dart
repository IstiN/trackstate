import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/pages/issue_detail_page.dart';
import '../../core/fakes/read_only_trackstate_repository.dart';
import '../../frameworks/flutter/widget_test_driver.dart';

class IssueDetailTestContext {
  IssueDetailTestContext._(this.page, this._tester);

  final IssueDetailPage page;
  final WidgetTester _tester;

  static Future<IssueDetailTestContext> launch(WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'read-only-token',
    });

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    final driver = WidgetTestDriver(tester);
    await driver.pumpApp(
      TrackStateApp(repository: ReadOnlyTrackStateRepository()),
    );

    return IssueDetailTestContext._(IssueDetailPage(driver), tester);
  }

  void resetView() {
    _tester.view.resetPhysicalSize();
    _tester.view.resetDevicePixelRatio();
  }
}
