import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/components/factories/testing_dependencies.dart';
import '../testing/core/interfaces/trackstate_app_component.dart';
import '../testing/tests/TS-809/support/ts809_dual_local_workspace_fixture.dart';
import '../testing/tests/TS-725/support/ts725_local_hosted_workspace_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'active local workspace row exposes Connect GitHub and opens auth dialog while signed out',
    (tester) async {
      final semantics = tester.ensureSemantics();
      Ts725LocalHostedWorkspaceFixture? fixture;
      Ts725LocalHostedWorkspaceScreen? screen;

      try {
        fixture = await Ts725LocalHostedWorkspaceFixture.create(tester);
        screen = await fixture.launch();
        await screen.waitForReady(
          Ts725LocalHostedWorkspaceFixture.activeLocalDisplayName,
        );

        await screen.openWorkspaceSwitcher();

        expect(
          screen.workspaceRowHasControl(
            fixture.activeLocalWorkspace.id,
            'Connect GitHub',
          ),
          isTrue,
        );

        expect(
          await screen.tapWorkspaceRowControl(
            fixture.activeLocalWorkspace.id,
            'Connect GitHub',
          ),
          isTrue,
        );

        expect(
          await screen.waitForAnyVisibleText(const <String>[
            'Connect GitHub',
            'Fine-grained token',
            'Connect token',
          ]),
          isTrue,
        );
        expect(screen.isLabeledTextFieldVisible('Fine-grained token'), isTrue);
        expect(screen.isControlVisible('Connect token'), isTrue);
      } finally {
        screen?.dispose();
        await fixture?.dispose();
        semantics.dispose();
      }
    },
  );

  testWidgets(
    'inactive local workspace row also exposes Connect GitHub while signed out',
    (tester) async {
      final semantics = tester.ensureSemantics();
      Ts809DualLocalWorkspaceFixture? fixture;
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);

      try {
        fixture = await Ts809DualLocalWorkspaceFixture.create();
        await screen.pumpWorkspaceProfileApp(
          workspaceProfileService: fixture.workspaceProfileService,
          openLocalRepository: fixture.openLocalRepository,
        );

        await screen.openWorkspaceSwitcher();

        expect(
          await screen.workspaceRowContainsText(
            fixture.inactiveLocalWorkspace.id,
            Ts809DualLocalWorkspaceFixture.inactiveLocalDisplayName,
          ),
          isTrue,
        );
        expect(
          await screen.workspaceRowContainsText(
            fixture.inactiveLocalWorkspace.id,
            'Active',
          ),
          isFalse,
        );
        expect(
          await screen.workspaceRowHasControl(
            fixture.inactiveLocalWorkspace.id,
            'Connect GitHub',
          ),
          isTrue,
        );
      } finally {
        await fixture?.dispose();
        semantics.dispose();
      }
    },
  );
}
