import 'dart:ui' show Tristate;
import 'package:flutter/foundation.dart';
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
    'condensed desktop workspace switcher keeps a single focusable button semantics node on web',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(1180, 900);
        tester.view.devicePixelRatio = 1;

        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        final trigger = find.byKey(const ValueKey('workspace-switcher-trigger'));
        final triggerSemanticsId = tester.getSemantics(trigger).id;
        final triggerSemantics = find.semantics.byPredicate(
          (node) => node.id == triggerSemanticsId,
          describeMatch: (_) => 'workspace switcher trigger semantics node',
        );
        final focusableButtonSemantics = find.semantics.descendant(
          of: triggerSemantics,
          matching: find.semantics.byPredicate(
            (node) {
              final data = node.getSemanticsData();
              return data.flagsCollection.isButton &&
                  data.flagsCollection.isFocused != Tristate.none;
            },
            describeMatch: (_) => 'focusable button semantics node',
          ),
          matchRoot: true,
        );

        expect(focusableButtonSemantics, kIsWeb ? findsOne : findsAtLeast(1));
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
