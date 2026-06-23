import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository_factory.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../TS-39/support/ts39_hosted_runtime_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'onboarding UI widget hierarchy is stable for automated probes',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      try {
        final repository = createTrackStateRepository(
          client: createHostedSetupClient(),
        );
        await tester.pumpWidget(TrackStateApp(repository: repository));

        final repositoryAccess = find.bySemanticsLabel(RegExp('Connect GitHub'));
        await _pumpUntilVisible(tester, repositoryAccess);

        // Stability check: the probed element remains present and unique
        // across multiple consecutive pump cycles.
        for (var i = 0; i < 5; i++) {
          await tester.pump(const Duration(milliseconds: 100));
          expect(repositoryAccess, findsOneWidget);
        }

        // Open the dialog and verify the descendant hierarchy is also stable.
        await tester.tap(repositoryAccess.first);
        await tester.pumpAndSettle();

        // The dialog title duplicates the action button text, so probe the
        // dialog-specific elements that are unique in the widget hierarchy.
        final fineGrainedToken = find.text('Fine-grained token');
        final tokenHelper = find.textContaining(
          'Needs Contents: read/write. Stored only on this device if remembered.',
        );
        final rememberOnThisBrowser = find.text('Remember on this browser');

        expect(fineGrainedToken, findsOneWidget);
        expect(tokenHelper, findsOneWidget);
        expect(rememberOnThisBrowser, findsOneWidget);

        for (var i = 0; i < 3; i++) {
          await tester.pump(const Duration(milliseconds: 100));
          expect(fineGrainedToken, findsOneWidget);
          expect(tokenHelper, findsOneWidget);
          expect(rememberOnThisBrowser, findsOneWidget);
        }
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}

Future<void> _pumpUntilVisible(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 5),
  Duration step = const Duration(milliseconds: 100),
}) async {
  final maxAttempts = timeout.inMilliseconds ~/ step.inMilliseconds;
  for (var attempt = 0; attempt < maxAttempts; attempt++) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Timed out waiting for the expected UI element.');
}
