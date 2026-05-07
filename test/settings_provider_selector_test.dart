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
    'settings provider selector reveals Local Git fields and clears hosted config',
    (tester) async {
      final semantics = tester.ensureSemantics();
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;

      try {
        await tester.pumpWidget(
          const TrackStateApp(repository: DemoTrackStateRepository()),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.bySemanticsLabel(RegExp('Settings')).first);
        await tester.pumpAndSettle();

        final providerSelector = find.bySemanticsLabel(
          RegExp('Repository access'),
        );
        final hostedProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Connect GitHub')),
        );
        final localGitProvider = find.descendant(
          of: providerSelector,
          matching: find.bySemanticsLabel(RegExp('Local Git')),
        );

        expect(providerSelector, findsOneWidget);
        expect(hostedProvider, findsOneWidget);
        expect(localGitProvider, findsOneWidget);

        await tester.tap(hostedProvider);
        await tester.pumpAndSettle();
        expect(find.text('Fine-grained token'), findsOneWidget);

        await tester.tap(localGitProvider);
        await tester.pumpAndSettle();

        expect(find.text('Repository Path'), findsOneWidget);
        expect(find.text('Write Branch'), findsOneWidget);
        expect(find.text('Fine-grained token'), findsNothing);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
