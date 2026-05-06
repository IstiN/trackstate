import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/utils/local_git_repository_fixture.dart';

void main() {
  testWidgets(
    'TS-43 local git mode resolves the configured author into the current session',
    (tester) async {
      late final LocalGitRepositoryFixture fixture;
      late final TrackerSnapshot snapshot;
      late final RepositoryUser resolvedUser;

      await tester.runAsync(() async {
        fixture = await LocalGitRepositoryFixture.create();
        final localRepository = LocalTrackStateRepository(
          repositoryPath: fixture.directory.path,
        );
        snapshot = await localRepository.loadSnapshot();
        resolvedUser = await localRepository.connect(fixture.connection);
      });

      addTearDown(fixture.dispose);
      final screen = TrackStateAppScreen(tester);
      addTearDown(screen.resetView);
      final repository = _ResolvedLocalGitRuntimeRepository(
        snapshot: snapshot,
        user: resolvedUser,
      );

      expect(resolvedUser.displayName, fixture.userName);
      expect(resolvedUser.login, fixture.userEmail);

      await screen.pumpApp(repository);
      screen.expectLocalRuntimeChrome();
      screen.expectInitials(resolvedUser.initials);

      final viewModel = screen.currentViewModel();
      expect(viewModel.connectedUser?.displayName, fixture.userName);
      expect(viewModel.connectedUser?.login, fixture.userEmail);

      await screen.openRepositoryAccess();
      screen.expectLocalRuntimeDialog(
        repositoryPath: fixture.directory.path,
        branch: fixture.branch,
      );
    },
  );
}

class _ResolvedLocalGitRuntimeRepository implements TrackStateRepository {
  const _ResolvedLocalGitRuntimeRepository({
    required this.snapshot,
    required this.user,
  });

  final TrackerSnapshot snapshot;
  final RepositoryUser user;

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async => user;

  @override
  Future<TrackerSnapshot> loadSnapshot() async => snapshot;

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async => snapshot.issues;

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');
}
