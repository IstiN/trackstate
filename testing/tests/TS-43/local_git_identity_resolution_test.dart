import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/utils/local_git_repository_fixture.dart';

void main() {
  testWidgets(
    'TS-43 local git mode resolves the configured author into the current session',
    (tester) async {
      final semantics = tester.ensureSemantics();
      final screen = TrackStateAppScreen(tester);
      LocalGitRepositoryFixture? fixture;

      try {
        await tester.runAsync(() async {
          fixture = await LocalGitRepositoryFixture.create();
        });
        addTearDown(fixture!.dispose);
        addTearDown(screen.resetView);

        await screen.pumpLocalGitApp(repositoryPath: fixture!.directory.path);
        screen.expectLocalRuntimeChrome();

        expect(screen.currentViewModel().usesLocalPersistence, isTrue);
        screen.expectInitials('LT');

        await screen.openJqlSearch();
        screen.expectVisibleLocalAuthorIdentity(
          userName: fixture!.userName,
          userEmail: fixture!.userEmail,
        );

        await screen.openRepositoryAccess();
        screen.expectLocalRuntimeDialog(
          repositoryPath: fixture!.directory.path,
          branch: fixture!.branch,
        );
      } finally {
        semantics.dispose();
      }
    },
  );
}
