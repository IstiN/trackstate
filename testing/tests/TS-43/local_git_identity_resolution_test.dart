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
        screen.expectLocalRuntimeChrome();
        screen.expectProfileIdentityVisible(
          displayName: 'Quincy Zebra',
          login: 'quincy.zebra+ts43@example.com',
          initials: 'QZ',
        );

        await screen.openRepositoryAccess();
        screen.expectLocalRuntimeDialog(
          repositoryPath: namedAuthorFixture.directory.path,
          branch: namedAuthorFixture.branch,
        );
        await screen.closeDialog('Close');

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
        screen.expectLocalRuntimeChrome();
        screen.expectProfileIdentityVisible(
          displayName: 'email.identity+ts43@example.com',
          login: 'email.identity+ts43@example.com',
          initials: 'EI',
        );

        await screen.openRepositoryAccess();
        screen.expectLocalRuntimeDialog(
          repositoryPath: emailFallbackFixture.directory.path,
          branch: emailFallbackFixture.branch,
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
