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
    'workspace switcher keeps Save and switch disabled in pristine state',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        const TrackStateApp(repository: DemoTrackStateRepository()),
      );
      await tester.pumpAndSettle();

      await tester.tap(
        find.bySemanticsLabel(RegExp(r'^Workspace switcher:')).last,
      );
      await tester.pumpAndSettle();

      final saveButton = tester.widget<FilledButton>(
        find.byKey(const ValueKey('workspace-add-button')),
      );

      expect(find.text('Save and switch'), findsOneWidget);
      expect(saveButton.onPressed, isNull);

      await tester.enterText(
        find.widgetWithText(TextFormField, 'Repository'),
        'alpha/repo',
      );
      await tester.pump();

      final enabledSaveButton = tester.widget<FilledButton>(
        find.byKey(const ValueKey('workspace-add-button')),
      );
      expect(enabledSaveButton.onPressed, isNotNull);
    },
  );
}
