import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/pages/trackstate_board_page.dart';
import '../../components/services/dirty_local_issue_save_service.dart';
import '../../core/utils/local_trackstate_fixture.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test(
    'TS-41 blocks a dirty main.md description save with actionable recovery guidance',
    () async {
      final fixture = await LocalTrackStateFixture.create();
      addTearDown(fixture.dispose);
      final service = DirtyLocalIssueSaveService(fixture);

      await fixture.makeDirtyMainFileChange();

      await expectLater(
        service.attemptDescriptionSave,
        throwsA(
          isA<TrackStateProviderException>().having(
            (error) => error.message,
            'message',
            allOf(contains('commit'), contains('stash'), contains('clean')),
          ),
        ),
      );
    },
  );

  testWidgets(
    'TS-41 shows an actionable visible error after a user-triggered mutation hits a dirty main.md',
    (tester) async {
      final page = TrackStateBoardPage(tester);
      const repository = _DirtyLocalRuntimeRepository();

      tester.view.physicalSize = const Size(1440, 960);
      tester.view.devicePixelRatio = 1;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await page.open(repository);
      await page.openBoard();

      expect(find.text('Local issue'), findsOneWidget);
      expect(find.text('In Progress'), findsOneWidget);

      await page.moveIssueToDone(LocalTrackStateFixture.issueKey);

      expect(page.errorBannerContaining('Move failed:'), findsOneWidget);
      expect(page.errorBannerContaining('commit'), findsOneWidget);
      expect(page.errorBannerContaining('stash'), findsOneWidget);
      expect(page.errorBannerContaining('clean'), findsOneWidget);
      expect(
        page.errorBannerContaining(LocalTrackStateFixture.issuePath),
        findsOneWidget,
      );
    },
  );
}

class _DirtyLocalRuntimeRepository implements TrackStateRepository {
  const _DirtyLocalRuntimeRepository();

  static const _issue = TrackStateIssue(
    key: LocalTrackStateFixture.issueKey,
    project: 'DEMO',
    issueType: IssueType.story,
    status: IssueStatus.inProgress,
    priority: IssuePriority.high,
    summary: 'Local issue',
    description: LocalTrackStateFixture.originalDescription,
    assignee: 'local-user',
    reporter: 'local-admin',
    labels: <String>[],
    components: <String>[],
    parentKey: null,
    epicKey: null,
    progress: 0.0,
    updatedLabel: 'just now',
    acceptanceCriteria: <String>['Can be loaded from local Git'],
    comments: <IssueComment>[],
    storagePath: LocalTrackStateFixture.issuePath,
  );

  static const _snapshot = TrackerSnapshot(
    project: ProjectConfig(
      key: 'DEMO',
      name: 'Local Demo',
      repository: '/tmp/local-demo',
      branch: 'main',
      issueTypes: <String>['Story'],
      statuses: <String>['To Do', 'In Progress', 'Done'],
      fields: <String>['Summary', 'Priority'],
    ),
    issues: <TrackStateIssue>[_issue],
  );

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async => _snapshot;

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async => _snapshot.issues;

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async {
    throw const TrackStateProviderException(
      'Cannot save DEMO/DEMO-1/main.md because it has staged or unstaged local changes.',
    );
  }
}
