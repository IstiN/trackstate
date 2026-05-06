import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

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

    await screen.pump(_UiLocalRepository());

    screen.expectTextVisible('Local Git');

    await screen.openSection('JQL Search');
    await screen.openIssue('DEMO-1', 'Local issue');

    screen.expectIssueDetailVisible('DEMO-1');
    screen.expectIssueDetailText('DEMO-1', 'Local issue');
    screen.expectIssueDetailText('DEMO-1', 'Loaded from local git.');
    screen.expectIssueDetailText('DEMO-1', 'Can be loaded from local Git');
    screen.expectIssueDetailText('DEMO-1', 'In Progress');

    await screen.openSection('Board');
    await screen.dragIssueToStatusColumn(
      key: 'DEMO-1',
      summary: 'Local issue',
      statusLabel: 'Done',
    );

    screen.expectTextVisible(
      'DEMO-1 moved to Done and committed to local Git branch main.',
    );

    await screen.openSection('JQL Search');
    screen.expectIssueDetailVisible('DEMO-1');
    screen.expectIssueDetailText('DEMO-1', 'Done');
  });

  test(
    'local Git mutation creates one isolated commit for the user action',
    () async {
      final repositoryFixture = await LocalGitTestRepository.create();
      addTearDown(repositoryFixture.dispose);

      final initialHead = await repositoryFixture.headRevision();
      final viewModel = TrackerViewModel(
        repository: LocalTrackStateRepository(
          repositoryPath: repositoryFixture.path,
        ),
      );

      await viewModel.load();
      await viewModel.moveIssue(viewModel.selectedIssue!, IssueStatus.done);

      expect(viewModel.message?.kind, TrackerMessageKind.localGitMoveCommitted);
      expect(viewModel.message?.issueKey, 'DEMO-1');
      expect(viewModel.message?.statusLabel, 'Done');
      expect(viewModel.message?.branch, 'main');
      expect(viewModel.selectedIssue?.status, IssueStatus.done);

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
    },
  );
}

class _UiLocalRepository implements TrackStateRepository {
  static const _project = ProjectConfig(
    key: 'DEMO',
    name: 'Local Demo',
    repository: '/tmp/local-demo',
    branch: 'main',
    issueTypes: ['Story'],
    statuses: ['To Do', 'In Progress', 'Done'],
    fields: ['Summary', 'Priority'],
  );

  TrackStateIssue _issue = const TrackStateIssue(
    key: 'DEMO-1',
    project: 'DEMO',
    issueType: IssueType.story,
    status: IssueStatus.inProgress,
    priority: IssuePriority.high,
    summary: 'Local issue',
    description: 'Loaded from local git.',
    assignee: 'local-user',
    reporter: 'local-admin',
    labels: [],
    components: [],
    parentKey: null,
    epicKey: null,
    progress: .35,
    updatedLabel: '2026-05-05T00:00:00Z',
    acceptanceCriteria: ['Can be loaded from local Git'],
    comments: [],
    storagePath: 'DEMO/DEMO-1/main.md',
  );

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(
        login: 'local@example.com',
        displayName: 'Local Tester',
      );

  @override
  Future<TrackerSnapshot> loadSnapshot() async =>
      TrackerSnapshot(project: _project, issues: [_issue]);

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async => [_issue];

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    _issue = _issue.copyWith(status: status, updatedLabel: 'just now');
    return _issue;
  }
}
