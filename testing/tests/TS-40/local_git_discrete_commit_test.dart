import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../core/utils/local_git_test_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('user sees the local Git move reflected in the UI', (
    tester,
  ) async {
    final TrackStateAppComponent screen = defaultTestingDependencies
        .createTrackStateAppScreen(tester);
    final repositoryFixture = await LocalGitTestRepository.create();
    addTearDown(repositoryFixture.dispose);
    final initialHead = await repositoryFixture.headRevision();

    await screen.pump(
      LocalTrackStateRepository(
        repositoryPath: repositoryFixture.path,
        processRunner: const SyncGitProcessRunner(),
      ),
    );
    await screen.expectTextVisible('Local Git');

    await screen.openSection('JQL Search');
    await screen.openIssue('DEMO-1', 'Local issue');
    await screen.expectIssueDetailText('DEMO-1', 'Local issue');
    await screen.expectIssueDetailText('DEMO-1', 'Loaded from local git.');
    await screen.expectIssueDetailText(
      'DEMO-1',
      'Can be loaded from local Git',
    );
    await screen.expectIssueDetailText('DEMO-1', 'In Progress');

    await screen.openSection('Board');
    await screen.dragIssueToStatusColumn(
      key: 'DEMO-1',
      summary: 'Local issue',
      sourceStatusLabel: 'In Progress',
      statusLabel: 'Done',
    );

    const successMessage =
        'DEMO-1 moved to Done and committed to local Git branch main.';
    await screen.expectTextVisible(successMessage);

    expect(await repositoryFixture.headRevision(), isNot(initialHead));
    expect(await repositoryFixture.parentOfHead(), initialHead);
    expect(
      await repositoryFixture.latestCommitSubject(),
      'Move DEMO-1 to Done',
    );
    expect(
      await repositoryFixture.latestCommitFiles(),
      equals(['DEMO/DEMO-1/main.md']),
    );
    expect(
      await repositoryFixture.readIssueMarkdown(),
      contains('status: Done'),
    );

    await screen.openSection('JQL Search');
    await screen.openIssue('DEMO-1', 'Local issue');
    await screen.expectIssueDetailText('DEMO-1', 'Done');
  });
}
