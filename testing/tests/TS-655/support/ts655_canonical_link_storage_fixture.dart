import 'dart:convert';
import '../../../fixtures/local_git_link_storage_fixture.dart';
import '../../../fixtures/provider_backed_local_git_link_storage_fixture.dart';

class Ts655CanonicalLinkStorageFixture {
  Ts655CanonicalLinkStorageFixture._(this._fixture);

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
  static const writeMessage =
      'Persist canonical outward link storage for TS-655';
  static const Map<String, String> validLinkRecord = <String, String>{
    'type': 'blocks',
    'target': targetIssueKey,
    'direction': 'outward',
  };

  String get repositoryPath => _fixture.repositoryPath;

  String get validLinksJsonContent =>
      _fixture.encodeLinksJson(<Map<String, String>>[validLinkRecord]);

  static Future<Ts655CanonicalLinkStorageFixture> create() async {
    return Ts655CanonicalLinkStorageFixture._(
      await createProviderBackedLocalGitLinkStorageFixture(
        config: const LocalGitLinkStorageFixtureConfig(
          ticketKey: 'TS-655',
          tempDirectoryPrefix: 'trackstate-ts-655-',
          seedCommitMessage: 'Seed canonical link fixture for TS-655',
          projectKey: projectKey,
          projectName: 'Mutation Demo',
          epicKey: epicKey,
          sourceIssueKey: sourceIssueKey,
          sourceIssueSummary: sourceIssueSummary,
          sourceIssueDescription:
              'Issue used as the source issue for TS-655 canonical link storage attempts.',
          targetIssueKey: targetIssueKey,
          targetIssueSummary: targetIssueSummary,
          targetIssueDescription:
              'Issue used as the linked target for TS-655 canonical link storage attempts.',
          sourceIssuePath: sourceIssuePath,
          targetIssuePath: targetIssuePath,
          sourceLinksPath: sourceLinksPath,
        ),
      ),
    );
  }

  Future<void> dispose() => _fixture.dispose();

  Future<Ts655RepositoryObservation> observeRepositoryState() async {
    return _fixture.observeRepositoryState();
  }

  Future<Ts655StorageAttemptObservation> attemptCanonicalLinksWrite() async {
    return _fixture.attemptLinksWrite(
      content: validLinksJsonContent,
      message: writeMessage,
    );
  }
}

typedef Ts655RepositoryObservation = LocalGitLinkStorageRepositoryObservation;
typedef Ts655StorageAttemptObservation = LocalGitLinkStorageAttemptObservation;
