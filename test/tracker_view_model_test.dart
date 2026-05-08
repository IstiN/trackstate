import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/ui/features/tracker/view_models/tracker_view_model.dart';

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
  Future<DeletedIssueTombstone> deleteIssue(TrackStateIssue issue) async =>
      throw const TrackStateRepositoryException(
        'Local runtime view-model repository does not support issue deletion.',
      );

  @override
  Future<TrackStateIssue> updateIssueStatus(
    TrackStateIssue issue,
    IssueStatus status,
  ) async => issue.copyWith(status: status, updatedLabel: 'just now');
}
