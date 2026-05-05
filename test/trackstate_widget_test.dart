import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('dashboard renders accessible navigation and actions', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('TrackState\\.AI')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Dashboard')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Connect GitHub')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Synced with Git')), findsWidgets);
      expect(find.textContaining('Platform Foundation'), findsWidgets);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });

  testWidgets('board navigation displays kanban columns and issue cards', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('To Do column')), findsOneWidget);
      expect(
        find.bySemanticsLabel(RegExp('In Progress column')),
        findsOneWidget,
      );
      expect(
        find.bySemanticsLabel(
          RegExp('Open TRACK-12 Implement Git sync service'),
        ),
        findsOneWidget,
      );
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });

  testWidgets('dragging a board card moves it to another status', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 960);
    tester.view.devicePixelRatio = 1;
    try {
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.bySemanticsLabel(RegExp('Board')).first);
      await tester.pumpAndSettle();

      final card = find.byWidgetPredicate(
        (widget) => widget is Draggable && widget.data is TrackStateIssue,
      );
      final doneColumn = find.bySemanticsLabel(RegExp('Done column'));

      await tester.timedDragFrom(
        tester.getCenter(card.at(1)),
        tester.getCenter(doneColumn) - tester.getCenter(card.at(1)),
        const Duration(milliseconds: 500),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('TRACK-12 moved locally'), findsOneWidget);
    } finally {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    }
  });

  testWidgets('theme toggle switches to dark mode', (tester) async {
    final semantics = tester.ensureSemantics();
    try {
      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      final context = tester.element(find.byType(Scaffold).first);
      expect(Theme.of(context).brightness, Brightness.light);

      await tester.tap(find.bySemanticsLabel(RegExp('Dark theme')));
      await tester.pumpAndSettle();

      final darkContext = tester.element(find.byType(Scaffold).first);
      expect(Theme.of(darkContext).brightness, Brightness.dark);
    } finally {
      semantics.dispose();
    }
  });
}
