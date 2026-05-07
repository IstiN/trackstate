// ignore_for_file: depend_on_referenced_packages

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import '../../components/screens/settings_screen_robot.dart';
import 'support/recording_url_launcher_platform.dart';
import 'support/ts71_broker_login_fixture.dart';

void main() {
  late UrlLauncherPlatform originalUrlLauncher;
  late RecordingUrlLauncherPlatform recordingUrlLauncher;

  setUp(() {
    originalUrlLauncher = UrlLauncherPlatform.instance;
    recordingUrlLauncher = RecordingUrlLauncherPlatform();
    UrlLauncherPlatform.instance = recordingUrlLauncher;
  });

  tearDown(() {
    UrlLauncherPlatform.instance = originalUrlLauncher;
  });

  testWidgets(
    'TS-71 launches the broker login and restores a user-scoped token with tracker data visible',
    (tester) async {
      final robot = SettingsScreenRobot(tester);
      final loggedOutFixture = Ts71BrokerLoginFixture();

      try {
        await robot.pumpApp(repository: loggedOutFixture.createRepository());

        expect(
          find.text(
            '${Ts71BrokerLoginFixture.issueKey} · ${Ts71BrokerLoginFixture.issueSummary}',
          ),
          findsOneWidget,
          reason:
              'The hosted runtime should populate the dashboard with tracker data from the fork before the user opens the GitHub connection flow.',
        );
        expect(
          loggedOutFixture.requestDescriptions,
          containsAll([
            'GET /repos/${Ts71BrokerLoginFixture.repositoryName}/git/trees/${Ts71BrokerLoginFixture.branch}',
            'GET /repos/${Ts71BrokerLoginFixture.repositoryName}/contents/TRACK/project.json',
            'GET /repos/${Ts71BrokerLoginFixture.repositoryName}/contents/TRACK/TRACK-71/main.md',
          ]),
          reason:
              'Opening the app should attempt the observable repository tree and contents reads needed to populate tracker data from the fork.',
        );

        await tester.tap(robot.connectGitHubTopBarControl);
        await tester.pumpAndSettle();

        expect(
          find.descendant(
            of: find.byType(AlertDialog),
            matching: find.text('Connect GitHub'),
          ),
          findsOneWidget,
          reason:
              'Opening the repository access dialog should show the user-facing Connect GitHub title.',
        );
        expect(
          find.widgetWithText(OutlinedButton, 'Continue with GitHub App'),
          findsOneWidget,
          reason:
              'The broker-based GitHub App path should be visible as a dedicated action in the dialog.',
        );
        expect(
          find.text('Fine-grained token'),
          findsOneWidget,
          reason:
              'The dialog should still show the manual token field so the user sees both supported authentication options.',
        );
        expect(
          find.text(
            'Needs Contents: read/write. Stored only on this device if remembered.',
          ),
          findsOneWidget,
          reason:
              'The helper copy should stay visible to the user while choosing how to authenticate.',
        );

        await tester.tap(
          find.widgetWithText(OutlinedButton, 'Continue with GitHub App'),
        );
        await tester.pumpAndSettle();

        final launchedUri = recordingUrlLauncher.lastLaunchedUri;
        expect(
          launchedUri,
          isNotNull,
          reason:
              'Tapping Continue with GitHub App should launch the external broker URL.',
        );
        expect(
          launchedUri!.scheme,
          'https',
          reason: 'The broker login should open a secure HTTPS URL.',
        );
        expect(
          launchedUri.host,
          'broker.example',
          reason:
              'The broker login should use the configured TRACKSTATE_GITHUB_AUTH_PROXY_URL host.',
        );
        expect(
          launchedUri.path,
          '/login',
          reason:
              'The broker login should preserve the configured proxy path when opening the external OAuth flow.',
        );
        expect(
          launchedUri.queryParameters['provider'],
          'github-app',
          reason:
              'The configured broker URL query parameters should be preserved when launching the OAuth broker.',
        );
        expect(
          launchedUri.queryParameters['repository'],
          Ts71BrokerLoginFixture.repositoryName,
          reason:
              'The broker launch should include the current repository so the backend can exchange a user-scoped token for the fork.',
        );
        expect(
          launchedUri.queryParameters['redirect_uri'],
          Uri.base.removeFragment().toString(),
          reason:
              'The broker launch should send the current app URL as the redirect target for the OAuth callback.',
        );
        expect(
          recordingUrlLauncher.lastWebOnlyWindowName,
          '_self',
          reason:
              'The hosted app should continue the broker login in the current browser tab so the callback returns to the running app.',
        );

        final connectedFixture = Ts71BrokerLoginFixture();
        await robot.pumpApp(
          repository: connectedFixture.createRepository(),
          sharedPreferences: {
            connectedFixture.tokenPreferenceKey:
                Ts71BrokerLoginFixture.exchangedToken,
          },
        );

        expect(
          find.text(
            'Connected as ${Ts71BrokerLoginFixture.connectedLogin} '
            'to ${Ts71BrokerLoginFixture.repositoryName}.',
          ),
          findsOneWidget,
          reason:
              'When the exchanged user token is present in browser storage, the app should restore the GitHub connection and show the connected banner text to the user.',
        );
        expect(
          find.text(
            '${Ts71BrokerLoginFixture.issueKey} · ${Ts71BrokerLoginFixture.issueSummary}',
          ),
          findsOneWidget,
          reason:
              'The tracker data should still be visible to the user after the broker-delivered token is restored.',
        );
        expect(
          connectedFixture.requestDescriptions,
          containsAll([
            'GET /repos/${Ts71BrokerLoginFixture.repositoryName}/git/trees/${Ts71BrokerLoginFixture.branch}',
            'GET /repos/${Ts71BrokerLoginFixture.repositoryName}/contents/TRACK/project.json',
            'GET /repos/${Ts71BrokerLoginFixture.repositoryName}/contents/TRACK/TRACK-71/main.md',
            'GET /repos/${Ts71BrokerLoginFixture.repositoryName}',
            'GET /user',
          ]),
          reason:
              'Restoring the user-scoped token should observe both the repository metadata call and the repository contents reads the UI depends on.',
        );
        expect(
          connectedFixture.bearerTokensForPath(
            '/repos/${Ts71BrokerLoginFixture.repositoryName}',
          ),
          [Ts71BrokerLoginFixture.exchangedToken],
          reason:
              'The repository metadata lookup should use the exchanged user-scoped token returned by the broker flow.',
        );
        expect(
          connectedFixture.bearerTokensForPath('/user'),
          [Ts71BrokerLoginFixture.exchangedToken],
          reason:
              'The user profile lookup should use the exchanged user-scoped token returned by the broker flow.',
        );

        await robot.openSettings();

        expect(
          robot.connectedTopBarControl,
          findsOneWidget,
          reason:
              'After the token is restored, the top-bar repository control should present the Connected state to the user.',
        );
        expect(
          robot.connectedSettingsControl,
          findsOneWidget,
          reason:
              'The Settings repository access section should mirror the Connected state after broker login restoration.',
        );
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
  );
}
