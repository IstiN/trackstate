import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'Project Settings renders Issue Types and their names without selecting a tab',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final visibleText = tester
            .widgetList<Text>(find.byType(Text))
            .map((widget) => widget.data?.trim())
            .whereType<String>()
            .join('\n');

        for (final expected in const [
          'Issue Types',
          'Epic',
          'Story',
          'Task',
          'Sub-task',
          'Bug',
        ]) {
          expect(
            visibleText,
            contains(expected),
            reason: 'Expected "$expected" to be visible on the Settings page',
          );
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}
