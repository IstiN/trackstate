import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import '../../components/screens/trackstate_app_screen.dart';
import '../../core/utils/local_git_test_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('user sees the local Git move reflected in the UI', (
    tester,
  ) async {
    final screen = TrackStateAppScreen(tester);
    final repositoryFixture = await LocalGitTestRepository.create();
    addTearDown(repositoryFixture.dispose);
    final initialHead = await repositoryFixture.headRevision();

    await screen.pump(
      LocalTrackStateRepository(
        repositoryPath: repositoryFixture.path,
        processRunner: const SyncGitProcessRunner(),
      ),
    );
    await screen.waitForTextVisible('Local Git');

    screen.expectTextVisible('Local Git');

    await screen.openSection('JQL Search');
    await screen.waitForIssueDetailVisible('DEMO-1');
    screen.expectIssueDetailVisible('DEMO-1');
    expect(find.text('Local issue'), findsWidgets);
    expect(find.textContaining('Loaded from local git.'), findsOneWidget);
    screen.expectTextVisible('Can be loaded from local Git');
    expect(find.text('In Progress'), findsWidgets);

    await screen.openSection('Board');
    await screen.dragIssueToStatusColumn(
      key: 'DEMO-1',
      summary: 'Local issue',
      sourceStatusLabel: 'In Progress',
      statusLabel: 'Done',
    );

    const successMessage =
        'DEMO-1 moved to Done and committed to local Git branch main.';
    await screen.waitForTextVisible(successMessage);
    screen.expectTextVisible(successMessage);

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
    await screen.waitForIssueDetailVisible('DEMO-1');
    expect(find.text('Done'), findsWidgets);
  });
}
