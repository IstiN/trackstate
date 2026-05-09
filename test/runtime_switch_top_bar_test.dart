import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/interfaces/trackstate_app_component.dart';
import '../testing/core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets(
    'switching from hosted settings to Local Git updates the Dashboard top bar without refresh',
    (tester) async {
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalTrackStateFixture? fixture;

      try {
        fixture = await tester.runAsync(LocalTrackStateFixture.create);
        if (fixture == null) {
          throw StateError('Local fixture creation did not complete.');
        }

        await screen.pump(const DemoTrackStateRepository());
        await screen.switchToLocalGitInSettings(
          repositoryPath: fixture.repositoryPath,
          writeBranch: 'main',
        );
        await screen.openSection('Dashboard');
        await screen.waitWithoutInteraction(const Duration(milliseconds: 150));

        expect(
          await screen.isTopBarSemanticsLabelVisible('Local Git') ||
              await screen.isTopBarTextVisible('Local Git'),
          isTrue,
        );
        expect(
          await screen.isTopBarSemanticsLabelVisible('Connect GitHub') ||
              await screen.isTopBarTextVisible('Connect GitHub'),
          isFalse,
        );
      } finally {
        await tester.runAsync(() async {
          if (fixture != null) {
            await fixture.dispose();
          }
        });
        screen.resetView();
      }
    },
  );
}
