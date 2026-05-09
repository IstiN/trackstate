import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/local_git_repository_fixture.dart';
import 'support/ts106_oauth_identity_fixture.dart';

void main() {
  testWidgets(
    'TS-106 hosted OAuth mode shows the remote profile identity instead of local Git metadata',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final robot = SettingsScreenRobot(tester);
      final hostedFixture = Ts106OauthIdentityFixture();

      try {
        final localAuthorFixture = (await tester.runAsync(
          () => LocalGitRepositoryFixture.create(
            userName: 'Local User',
            userEmail: 'local.user@example.com',
          ),
        ))!;
        addTearDown(localAuthorFixture.dispose);

        await robot.pumpApp(
          repository: hostedFixture.createRepository(),
          sharedPreferences: {
            hostedFixture.tokenPreferenceKey:
                Ts106OauthIdentityFixture.remoteToken,
          },
        );

        expect(
          robot.connectedTopBarControl,
          findsOneWidget,
          reason:
              'The hosted runtime should restore the stored remote session and expose the Connected top-bar control in OAuth mode.',
        );
        expect(
          find.text(
            '${Ts106OauthIdentityFixture.issueKey} · '
            '${Ts106OauthIdentityFixture.issueSummary}',
          ),
          findsOneWidget,
          reason:
              'The hosted repository snapshot should still load tracker data while the remote session is active.',
        );

        robot.expectTopBarProfileIdentityVisible(
          displayName: Ts106OauthIdentityFixture.remoteDisplayName,
          login: Ts106OauthIdentityFixture.remoteLogin,
          initials: 'RU',
        );
        robot.expectTopBarProfileIdentityAbsent(localAuthorFixture.userName);
        robot.expectTopBarProfileIdentityAbsent(localAuthorFixture.userEmail);

        expect(
          hostedFixture.bearerTokensForPath('/user'),
          [Ts106OauthIdentityFixture.remoteToken],
          reason:
              'Restoring the hosted session should resolve the remote profile from the stored OAuth token, not from local Git metadata.',
        );
        final repositoryTokens = hostedFixture.bearerTokensForPath(
          '/repos/${Ts106OauthIdentityFixture.repositoryName}',
        );
        expect(
          repositoryTokens,
          isNotEmpty,
          reason:
              'Restoring the hosted session should perform at least one authenticated repository permission lookup.',
        );
        expect(
          repositoryTokens.every(
            (token) => token == Ts106OauthIdentityFixture.remoteToken,
          ),
          isTrue,
          reason:
              'Every repository permission lookup should use the stored remote session token once the hosted runtime restores the connection.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
        semantics.dispose();
      }
    },
  );
}
