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
    'desktop workspace switcher exports focusable button semantics',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1440, 960);
        tester.view.devicePixelRatio = 1;

        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final triggerNode = tester.getSemantics(
          find.bySemanticsLabel(RegExp('^Workspace switcher:')).last,
        );
        final triggerSemantics = triggerNode.getSemanticsData();

      expect(triggerSemantics.flagsCollection.isButton, isTrue);
      expect(
        triggerSemantics.flagsCollection.isFocusable,
        isTrue,
        reason:
            'The exported workspace switcher semantics node must be keyboard focusable '
              'so Flutter web can map it to a tabbable browser control.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
