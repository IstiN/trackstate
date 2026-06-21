import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/utils/local_git_repository_fixture.dart';

void main() {
  testWidgets(
    'TS-43 local git mode renders the resolved local author on the profile surface',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = defaultTestingDependencies.createTrackStateAppScreen(
        tester,
      );

      Future<void> widenViewport() async {
        // The top-bar profile surface collapses to initials-only in the
        // condensed desktop layout. Use a wide viewport so the resolved author
        // display name is rendered as visible text.
        tester.view.physicalSize = const Size(1920, 1080);
        await tester.pumpAndSettle();
      }

      try {
        final namedAuthorFixture = (await tester.runAsync(
          () => LocalGitRepositoryFixture.create(
            userName: 'Quincy Zebra',
            userEmail: 'quincy.zebra+ts43@example.com',
          ),
        ))!;
        addTearDown(namedAuthorFixture.dispose);
        addTearDown(screen.resetView);

        await screen.pumpLocalGitApp(
          repositoryPath: namedAuthorFixture.directory.path,
        );
        await widenViewport();
        screen.expectLocalRuntimeChrome();
        screen.expectProfileIdentityVisible(
          displayName: 'Quincy Zebra',
          login: 'quincy.zebra+ts43@example.com',
          initials: 'QZ',
        );

        final emailFallbackFixture = (await tester.runAsync(
          () => LocalGitRepositoryFixture.create(
            userName: 'Commit Author',
            userEmail: 'email.identity+ts43@example.com',
          ),
        ))!;
        addTearDown(emailFallbackFixture.dispose);
        await tester.runAsync(
          () => emailFallbackFixture.configureAuthor(
            userName: '',
            userEmail: 'email.identity+ts43@example.com',
          ),
        );

        await screen.pumpLocalGitApp(
          repositoryPath: emailFallbackFixture.directory.path,
        );
        await widenViewport();
        screen.expectLocalRuntimeChrome();
        screen.expectProfileIdentityVisible(
          displayName: 'email.identity+ts43@example.com',
          login: 'email.identity+ts43@example.com',
          initials: 'EI',
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
