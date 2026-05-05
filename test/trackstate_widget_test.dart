import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  testWidgets('dashboard renders accessible navigation and actions', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      await tester.pumpWidget(const TrackStateApp());
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel(RegExp('TrackState\\.AI')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Dashboard')), findsWidgets);
      expect(find.bySemanticsLabel(RegExp('Create issue')), findsWidgets);
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
      await tester.pumpWidget(const TrackStateApp());
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

  testWidgets('theme toggle switches to dark mode', (tester) async {
    final semantics = tester.ensureSemantics();
    try {
      await tester.pumpWidget(const TrackStateApp());
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
