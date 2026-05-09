import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import 'ts135_archived_issue_fixture.dart';

typedef _LoadSnapshotMethod = Future<TrackerSnapshot> Function();
typedef _SearchIssuesMethod =
    Future<List<TrackStateIssue>> Function(String jql);
typedef _ConnectMethod =
    Future<RepositoryUser> Function(RepositoryConnection connection);
typedef _ArchiveIssueMethod =
    Future<TrackStateIssue> Function(TrackStateIssue issue);
typedef _DeleteIssueMethod =
    Future<DeletedIssueTombstone> Function(TrackStateIssue issue);
typedef _CreateIssueMethod =
    Future<TrackStateIssue> Function({
      required String summary,
      String description,
      Map<String, String> customFields,
    });
typedef _UpdateIssueDescriptionMethod =
    Future<TrackStateIssue> Function(TrackStateIssue issue, String description);
typedef _UpdateIssueStatusMethod =
    Future<TrackStateIssue> Function(TrackStateIssue issue, IssueStatus status);

class Ts154RepositoryContractFixture {
  Ts154RepositoryContractFixture._({
    required Ts135ArchivedIssueFixture archiveFixture,
  }) : _archiveFixture = archiveFixture;

  final Ts135ArchivedIssueFixture _archiveFixture;

  static const validatedMethodNames = <String>[
    'loadSnapshot',
    'searchIssues',
    'connect',
    'archiveIssue',
    'deleteIssue',
    'createIssue',
    'updateIssueDescription',
    'updateIssueStatus',
  ];

  static Future<Ts154RepositoryContractFixture> create() async {
    final archiveFixture = await Ts135ArchivedIssueFixture.create();
    return Ts154RepositoryContractFixture._(archiveFixture: archiveFixture);
  }

  Future<void> dispose() => _archiveFixture.dispose();

  LocalTrackStateRepository createRepository() =>
      LocalTrackStateRepository(repositoryPath: _archiveFixture.directory.path);

  Future<Ts154RepositoryContractObservation> observeContract() async {
    final repository = createRepository();
    final typedRepository = repository as TrackStateRepository;
    final dynamic dynamicRepository = repository;

    final validatedMethods = <String>[
      _validateMethod(
        'loadSnapshot',
        () => dynamicRepository.loadSnapshot as _LoadSnapshotMethod,
      ),
      _validateMethod(
        'searchIssues',
        () => dynamicRepository.searchIssues as _SearchIssuesMethod,
      ),
      _validateMethod(
        'connect',
        () => dynamicRepository.connect as _ConnectMethod,
      ),
      _validateMethod(
        'archiveIssue',
        () => dynamicRepository.archiveIssue as _ArchiveIssueMethod,
      ),
      _validateMethod(
        'deleteIssue',
        () => dynamicRepository.deleteIssue as _DeleteIssueMethod,
      ),
      _validateMethod(
        'createIssue',
        () => dynamicRepository.createIssue as _CreateIssueMethod,
      ),
      _validateMethod(
        'updateIssueDescription',
        () =>
            dynamicRepository.updateIssueDescription
                as _UpdateIssueDescriptionMethod,
      ),
      _validateMethod(
        'updateIssueStatus',
        () => dynamicRepository.updateIssueStatus as _UpdateIssueStatusMethod,
      ),
    ];

    return Ts154RepositoryContractObservation(
      repositoryType: repository.runtimeType.toString(),
      usesLocalPersistence: typedRepository.usesLocalPersistence,
      supportsGitHubAuth: typedRepository.supportsGitHubAuth,
      validatedMethodNames: List<String>.unmodifiable(validatedMethods),
      beforeArchival: await _archiveFixture.observeBeforeArchivalState(),
    );
  }

  Future<Ts154RepositoryArchiveObservation>
  archiveIssueThroughDynamicContract() async {
    final dynamic repository = createRepository();
    final snapshot = await repository.loadSnapshot() as TrackerSnapshot;
    final issue = snapshot.issues.singleWhere(
      (candidate) =>
          candidate.key == Ts135ArchivedIssueFixture.archivedIssueKey,
    );
    final archivedIssue =
        await repository.archiveIssue(issue) as TrackStateIssue;

    return Ts154RepositoryArchiveObservation(
      archivedIssue: archivedIssue,
      afterArchival: await _archiveFixture.observeBeforeArchivalState(),
    );
  }

  String _validateMethod<T>(String methodName, T Function() getter) {
    try {
      getter();
      return methodName;
    } on NoSuchMethodError catch (error) {
      throw StateError(
        'LocalTrackStateRepository is missing required method '
        '$methodName: ${error.toString()}',
      );
    }
  }
}

class Ts154RepositoryContractObservation {
  const Ts154RepositoryContractObservation({
    required this.repositoryType,
    required this.usesLocalPersistence,
    required this.supportsGitHubAuth,
    required this.validatedMethodNames,
    required this.beforeArchival,
  });

  final String repositoryType;
  final bool usesLocalPersistence;
  final bool supportsGitHubAuth;
  final List<String> validatedMethodNames;
  final Ts135ArchivedIssueObservation beforeArchival;
}

class Ts154RepositoryArchiveObservation {
  const Ts154RepositoryArchiveObservation({
    required this.archivedIssue,
    required this.afterArchival,
  });

  final TrackStateIssue archivedIssue;
  final Ts135ArchivedIssueObservation afterArchival;
}
