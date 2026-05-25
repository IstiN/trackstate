import 'dart:convert';
import '../../../fixtures/local_git_link_storage_fixture.dart';
import '../../../fixtures/provider_backed_local_git_link_storage_fixture.dart';

class Ts627NonCanonicalLinkStorageFixture {
  Ts627NonCanonicalLinkStorageFixture._(this._fixture);

  final LocalGitLinkStorageFixture _fixture;

  static const projectKey = 'DEMO';
  static const epicKey = 'DEMO-1';
  static const sourceIssueKey = 'DEMO-2';
  static const sourceIssueSummary = 'Source story';
  static const targetIssueKey = 'DEMO-10';
  static const targetIssueSummary = 'Blocking epic';
  static const sourceIssuePath = 'DEMO/DEMO-1/DEMO-2/main.md';
  static const targetIssuePath = 'DEMO/DEMO-10/main.md';
  static const sourceLinksPath = 'DEMO/DEMO-1/DEMO-2/links.json';
  static const writeMessage = 'Attempt non-canonical link storage for TS-627';
  static const Map<String, String> invalidLinkRecord = <String, String>{
    'type': 'blocks',
    'target': targetIssueKey,
    'direction': 'inward',
  };

  String get repositoryPath => _fixture.repositoryPath;

  String get invalidLinksJsonContent =>
      _fixture.encodeLinksJson(<Map<String, String>>[invalidLinkRecord]);

  static Future<Ts627NonCanonicalLinkStorageFixture> create() async {
    return Ts627NonCanonicalLinkStorageFixture._(
      await createProviderBackedLocalGitLinkStorageFixture(
        config: const LocalGitLinkStorageFixtureConfig(
          ticketKey: 'TS-627',
          tempDirectoryPrefix: 'trackstate-ts-627-',
          seedCommitMessage: 'Seed non-canonical link fixture for TS-627',
          projectKey: projectKey,
          projectName: 'Mutation Demo',
          epicKey: epicKey,
          sourceIssueKey: sourceIssueKey,
          sourceIssueSummary: sourceIssueSummary,
          sourceIssueDescription:
              'Issue used as the source issue for TS-627 invalid link storage attempts.',
          targetIssueKey: targetIssueKey,
          targetIssueSummary: targetIssueSummary,
          targetIssueDescription:
              'Issue used as the linked target for TS-627 invalid link storage attempts.',
          sourceIssuePath: sourceIssuePath,
          targetIssuePath: targetIssuePath,
          sourceLinksPath: sourceLinksPath,
        ),
      ),
    );
  }

  Future<void> dispose() => _fixture.dispose();

  Future<Ts627RepositoryObservation> observeRepositoryState() async {
    return _fixture.observeRepositoryState();
  }

  Future<Ts627StorageAttemptObservation> attemptInvalidLinksWrite() async {
    return _fixture.attemptLinksWrite(
      content: invalidLinksJsonContent,
      message: writeMessage,
    );
  }
}

typedef Ts627RepositoryObservation = LocalGitLinkStorageRepositoryObservation;
typedef Ts627StorageAttemptObservation = LocalGitLinkStorageAttemptObservation;
