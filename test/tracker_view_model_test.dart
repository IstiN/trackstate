import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

import '../testing/core/fakes/reactive_issue_detail_trackstate_repository.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('view model loads snapshot and default search results', () async {
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );

    await viewModel.load();

    expect(viewModel.project?.key, 'TRACK');
    expect(viewModel.selectedIssue?.key, 'TRACK-12');
    expect(viewModel.searchResults, isNotEmpty);
  });

  test('view model changes sections and toggles theme', () async {
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );
    await viewModel.load();

    viewModel.selectSection(TrackerSection.board);
    viewModel.toggleTheme();

    expect(viewModel.section, TrackerSection.board);
    expect(viewModel.themePreference, ThemePreference.dark);
  });

  test('view model restores remembered GitHub token', () async {
    SharedPreferences.setMockInitialValues({
      'trackstate.githubToken.trackstate.trackstate': 'stored-token',
    });
    final viewModel = TrackerViewModel(
      repository: const DemoTrackStateRepository(),
    );

    await viewModel.load();

    expect(viewModel.isConnected, isTrue);
    expect(viewModel.connectedUser?.initials, 'DU');
  });

  test(
    'view model loads the local repository user for avatar details',
    () async {
      final viewModel = TrackerViewModel(
        repository: const _LocalRuntimeRepository(),
      );

      await viewModel.load();

      expect(viewModel.connectedUser?.displayName, 'Local User');
      expect(viewModel.connectedUser?.initials, 'LU');
    },
  );

  test(
    'view model reports local persistence after a successful move',
    () async {
      final viewModel = TrackerViewModel(
        repository: const _LocalRuntimeRepository(),
      );

      await viewModel.load();
      await viewModel.moveIssue(viewModel.selectedIssue!, IssueStatus.done);

      expect(viewModel.message?.kind, TrackerMessageKind.localGitMoveCommitted);
    },
  );

  test(
    'view model reacts to live provider session capability downgrades',
    () async {
      SharedPreferences.setMockInitialValues({
        'trackstate.githubToken.trackstate.trackstate': 'write-enabled-token',
      });
      final repository = ReactiveIssueDetailTrackStateRepository();
      final viewModel = TrackerViewModel(repository: repository);
      var notificationCount = 0;
      viewModel.addListener(() {
        notificationCount += 1;
      });

      await viewModel.load();

      expect(viewModel.hasReadOnlySession, isFalse);

      notificationCount = 0;
      repository.synchronizeSessionToReadOnly();

      expect(viewModel.hasReadOnlySession, isTrue);
      expect(
        notificationCount,
        greaterThan(0),
        reason:
            'Expected the view model to notify listeners when the active provider session becomes read-only.',
      );
      viewModel.dispose();
    },
  );

  test(
    'view model preserves return context when opening an issue detail',
    () async {
      final viewModel = TrackerViewModel(
        repository: const DemoTrackStateRepository(),
      );
      await viewModel.load();

      final issue = viewModel.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );
      viewModel.selectIssue(issue, returnSection: TrackerSection.board);

      expect(viewModel.section, TrackerSection.search);
      expect(viewModel.issueDetailReturnSection, TrackerSection.board);

      viewModel.returnFromIssueDetail();

      expect(viewModel.section, TrackerSection.board);
      expect(viewModel.issueDetailReturnSection, isNull);
    },
  );

  test(
    'view model uses shared mutations and preserves the origin after create',
    () async {
      final repository = const DemoTrackStateRepository();
      final createdIssue = TrackStateIssue(
        key: 'TRACK-99',
        project: 'TRACK',
        issueType: IssueType.story,
        issueTypeId: 'story',
        status: IssueStatus.todo,
        statusId: 'todo',
        priority: IssuePriority.medium,
        priorityId: 'medium',
        summary: 'Created through view model',
        description: 'Uses shared mutation result.',
        assignee: 'demo-user',
        reporter: 'demo-user',
        labels: const ['ux'],
        components: const [],
        fixVersionIds: const [],
        watchers: const [],
        customFields: const {},
        parentKey: null,
        epicKey: 'TRACK-1',
        parentPath: null,
        epicPath: 'TRACK/TRACK-1',
        progress: 0,
        updatedLabel: 'just now',
        acceptanceCriteria: const [],
        comments: const [],
        links: const [],
        attachments: const [],
        isArchived: false,
        storagePath: 'TRACK/TRACK-1/TRACK-99/main.md',
        rawMarkdown: '',
      );
      final viewModel = TrackerViewModel(
        repository: repository,
        issueMutationService: _RecordingIssueMutationService(createdIssue),
      );

      await viewModel.load();

      final success = await viewModel.createIssue(
        summary: 'Created through view model',
        description: 'Uses shared mutation result.',
        issueTypeId: 'story',
        priorityId: 'medium',
        assignee: 'demo-user',
        epicKey: 'TRACK-1',
        labels: const ['ux'],
        returnSection: TrackerSection.hierarchy,
      );

      expect(success, isTrue);
      expect(viewModel.section, TrackerSection.search);
      expect(viewModel.issueDetailReturnSection, TrackerSection.hierarchy);
      expect(viewModel.selectedIssue?.key, 'TRACK-99');
    },
  );
}

class _LocalRuntimeRepository implements TrackStateRepository {
  const _LocalRuntimeRepository();

  static const _demoRepository = DemoTrackStateRepository();

  @override
  bool get supportsGitHubAuth => false;

  @override
  bool get usesLocalPersistence => true;

  @override
  Future<RepositoryUser> connect(RepositoryConnection connection) async =>
      const RepositoryUser(login: 'local-user', displayName: 'Local User');

  @override
  Future<TrackerSnapshot> loadSnapshot() async =>
      _demoRepository.loadSnapshot();

  @override
  Future<List<TrackStateIssue>> searchIssues(String jql) async =>
      _demoRepository.searchIssues(jql);

  @override
  Future<TrackStateIssue> archiveIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime view-model repository does not support issue archiving.',
      );

  @override
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime view-model repository does not support issue deletion.',
      );

  @override
  Future<TrackStateIssue> createIssue({
    required String summary,
    String description = '',
    Map<String, String> customFields = const {},
  }) async {
    throw UnimplementedError('Issue creation is not implemented.');
  }

  @override
  Future<TrackStateIssue> updateIssueDescription(
    TrackStateIssue issue,
    String description,
  ) async =>
      issue.copyWith(description: description.trim(), updatedLabel: 'just now');

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');
}

class _RecordingIssueMutationService extends IssueMutationService {
  _RecordingIssueMutationService(this._created)
    : super(repository: const DemoTrackStateRepository());

  final TrackStateIssue _created;

  @override
  Future<IssueMutationResult<TrackStateIssue>> createIssue({
    required String summary,
    String description = '',
    String? issueTypeId,
    String? priorityId,
    String? assignee,
    String? reporter,
    String? parentKey,
    String? epicKey,
    Map<String, Object?> fields = const {},
  }) async => IssueMutationResult.success(
    operation: 'create',
    issueKey: _created.key,
    value: _created,
  );
}
