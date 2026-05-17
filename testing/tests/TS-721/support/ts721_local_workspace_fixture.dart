import '../../../core/utils/local_git_repository_fixture.dart';

class Ts721LocalWorkspaceFixture {
  Ts721LocalWorkspaceFixture._(this._repositoryFixture);

  static const expectedDisplayName = 'TS-721 Local Demo';
  static const expectedProjectName = 'Local Demo';
  static const expectedIssueSummary = 'Local identity issue';
  static const expectedBranch = 'main';

  final LocalGitRepositoryFixture _repositoryFixture;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts721LocalWorkspaceFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-721 Tester',
      userEmail: 'ts721@example.com',
    );
    return Ts721LocalWorkspaceFixture._(repositoryFixture);
  }

  Future<void> dispose() => _repositoryFixture.dispose();
}
