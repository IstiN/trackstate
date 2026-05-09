import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

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
  TrackerViewModel? _viewModel;

  @override
  Future<void> launch() async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
    });

    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;

    final driver = WidgetTestDriver(tester);
    await driver.pumpApp(TrackStateApp(repository: repository));
    _viewModel = _trackerViewModel;
  }

  @override
  Future<void> synchronizeSessionToReadOnly() async {
    repository.synchronizeSessionToReadOnly();
    _viewModel?.notifyListeners();
    await tester.pump();
    await tester.pumpAndSettle();
  }

  @override
  void dispose() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  }

  TrackerViewModel? get _trackerViewModel {
    final builders = find.byType(ListenableBuilder);
    if (builders.evaluate().isEmpty) {
      return null;
    }
    final builder = tester.widget<ListenableBuilder>(builders.first);
    final listenable = builder.listenable;
    return listenable is TrackerViewModel ? listenable : null;
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
