import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

class DirtyLocalIssueFlowRobot {
  DirtyLocalIssueFlowRobot(this.tester);

  final WidgetTester tester;

  Finder get boardNavigation => find.text('Board').first;
  Finder get inProgressColumn => find.bySemanticsLabel('In Progress column');
  Finder get doneColumn => find.bySemanticsLabel('Done column');

  Finder issueCard(String issueKey, String summary) =>
      find.bySemanticsLabel('Open $issueKey $summary');

  Future<void> pumpApp({
    required TrackStateRepository repository,
    Map<String, Object> sharedPreferences = const {},
  }) async {
    SharedPreferences.setMockInitialValues(sharedPreferences);
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    await tester.pumpWidget(
      TrackStateApp(key: UniqueKey(), repository: repository),
    );
    await _pumpFrames();
  }

  Future<void> openBoard() async {
    await tester.tap(boardNavigation);
    await _pumpFrames();
  }

  Future<void> moveIssueToDone(String issueKey, String summary) async {
    final card = issueCard(issueKey, summary);
    await tester.ensureVisible(card);
    final from = tester.getCenter(card);
    final to = tester.getCenter(doneColumn);
    final gesture = await tester.startGesture(from);
    await tester.pump(const Duration(milliseconds: 100));
    await gesture.moveTo(to);
    await tester.pump(const Duration(milliseconds: 300));
    await gesture.up();
    await _pumpFrames();
  }

  String? currentBannerText() {
    for (final widget in tester.widgetList<Text>(find.byType(Text))) {
      final text = widget.data?.trim();
      if (text != null && text.startsWith('Move failed:')) {
        return text;
      }
    }
    return null;
  }

  Future<void> _pumpFrames([int count = 12]) async {
    await tester.pump();
    for (var i = 0; i < count; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }
}
