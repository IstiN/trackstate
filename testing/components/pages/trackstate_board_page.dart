import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

class TrackStateBoardPage {
  const TrackStateBoardPage(this.tester);

  final WidgetTester tester;

  Future<void> open(TrackStateRepository repository) async {
    await tester.pumpWidget(TrackStateApp(repository: repository));
    await _pumpUntil(find.bySemanticsLabel(RegExp('Board')).first);
  }

  Future<void> openBoard() async {
    await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
    await _pumpUntil(find.bySemanticsLabel(RegExp('Done column')));
  }

  Future<void> moveIssueToDone(String issueKey) async {
    final card = find.byWidgetPredicate((widget) {
      if (widget is! Draggable<TrackStateIssue>) {
        return false;
      }
      return widget.data?.key == issueKey;
    });
    final doneColumn = find.bySemanticsLabel(RegExp('Done column'));

    await tester.timedDragFrom(
      tester.getCenter(card),
      tester.getCenter(doneColumn) - tester.getCenter(card),
      const Duration(milliseconds: 500),
    );
    await _pumpFrames();
  }

  Finder errorBannerContaining(String text) => find.textContaining(text);

  Future<void> _pumpUntil(Finder finder) async {
    for (var attempt = 0; attempt < 20; attempt++) {
      await _pumpFrames();
      if (finder.evaluate().isNotEmpty) {
        return;
      }
    }
    throw TestFailure('Timed out waiting for the expected UI element.');
  }

  Future<void> _pumpFrames() async {
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 200));
  }
}
