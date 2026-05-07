import 'package:flutter_test/flutter_test.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/utils/local_git_repository_fixture.dart';

void main() {
  testWidgets(
    'TS-43 local git mode resolves the configured author into the current session',
    (tester) async {
      late final LocalGitRepositoryFixture fixture;

      await tester.runAsync(() async {
        fixture = await LocalGitRepositoryFixture.create();
      });

      addTearDown(fixture.dispose);
      final screen = TrackStateAppScreen(tester);
      addTearDown(screen.resetView);

      await screen.pumpLocalGitApp(repositoryPath: fixture.directory.path);
      screen.expectLocalRuntimeChrome();

      final viewModel = screen.currentViewModel();
      expect(viewModel.usesLocalPersistence, isTrue);
      expect(viewModel.connectedUser?.displayName, fixture.userName);
      expect(viewModel.connectedUser?.login, fixture.userEmail);
      screen.expectInitials(viewModel.connectedUser!.initials);

      await screen.openRepositoryAccess();
      screen.expectLocalRuntimeDialog(
        repositoryPath: fixture.directory.path,
        branch: fixture.branch,
      );
    },
  );
}
