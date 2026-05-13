import 'invalid_workflow_transition_fixture.dart';

const _scenario = InvalidWorkflowTransitionScenario(
  tempDirectoryPrefix: 'trackstate-ts-621-',
  projectName: 'TrackState TS-621',
  issueKey: 'TRACK-621',
  issueSummary: 'Reject illegal To Do to Done workflow transition',
  assignee: 'ts621-user',
  reporter: 'ts621-user',
  seedAuthorName: 'TS-621 Tester',
  seedAuthorEmail: 'ts621@example.com',
  seedCommitSubject: 'Seed TS-621 invalid workflow transition fixture',
);

class Ts621InvalidWorkflowTransitionFixture {
  Ts621InvalidWorkflowTransitionFixture._(this._fixture);

  final InvalidWorkflowTransitionFixture _fixture;

  static String get projectKey => _scenario.projectKey;
  static String get issueKey => _scenario.issueKey;
  static String get issuePath => _scenario.issuePath;
  static String get workflowsPath => _scenario.workflowsPath;
  static String get issueSummary => _scenario.issueSummary;
  static String get issueDescription => _scenario.issueDescription;
  static String get todoStatusId => _scenario.todoStatusId;
  static String get todoStatusLabel => _scenario.todoStatusLabel;
  static String get inProgressStatusId => _scenario.inProgressStatusId;
  static String get inProgressStatusLabel => _scenario.inProgressStatusLabel;
  static String get doneStatusId => _scenario.doneStatusId;
  static String get doneStatusLabel => _scenario.doneStatusLabel;
  static String get expectedFailureMessage => _scenario.expectedFailureMessage;

  String get repositoryPath => _fixture.repositoryPath;

  static Future<Ts621InvalidWorkflowTransitionFixture> create() async {
    return Ts621InvalidWorkflowTransitionFixture._(
      await InvalidWorkflowTransitionFixture.create(_scenario),
    );
  }

  Future<void> dispose() => _fixture.dispose();

  Future<Ts621PersistedRepositoryObservation>
  observePersistedRepositoryState() {
    return _fixture.observePersistedRepositoryState();
  }
}

typedef Ts621PersistedRepositoryObservation = PersistedRepositoryObservation;
