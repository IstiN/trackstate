import 'invalid_workflow_transition_fixture.dart';

const _scenario = InvalidWorkflowTransitionScenario(
  tempDirectoryPrefix: 'trackstate-ts-599-',
  projectName: 'TrackState TS-599',
  issueKey: 'TRACK-599',
  issueSummary: 'Block direct To Do to Done transitions',
  assignee: 'ts599-user',
  reporter: 'ts599-user',
  seedAuthorName: 'TS-599 Tester',
  seedAuthorEmail: 'ts599@example.com',
  seedCommitSubject: 'Seed TS-599 invalid workflow transition fixture',
);

class Ts599InvalidWorkflowTransitionFixture {
  Ts599InvalidWorkflowTransitionFixture._(this._fixture);

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

  static Future<Ts599InvalidWorkflowTransitionFixture> create() async {
    return Ts599InvalidWorkflowTransitionFixture._(
      await InvalidWorkflowTransitionFixture.create(_scenario),
    );
  }

  Future<void> dispose() => _fixture.dispose();

  Future<Ts599PersistedRepositoryObservation>
  observePersistedRepositoryState() {
    return _fixture.observePersistedRepositoryState();
  }
}

typedef Ts599PersistedRepositoryObservation = PersistedRepositoryObservation;
