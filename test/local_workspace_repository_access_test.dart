import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../testing/tests/TS-725/support/ts725_local_hosted_workspace_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'active local workspace settings exposes Connect GitHub for the TS-725 auth step',
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

        await screen.openSettings();

        expect(
          screen.isControlVisible('Connect GitHub') ||
              screen.isTextVisible('Connect GitHub') ||
              screen.isSemanticsLabelVisible('Connect GitHub'),
          isTrue,
        );
      } finally {
        screen?.dispose();
        await fixture?.dispose();
        semantics.dispose();
      }
    },
  );
}
