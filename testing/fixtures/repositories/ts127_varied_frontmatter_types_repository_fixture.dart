import 'dart:convert';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/issue_resolution_service.dart';
import '../../core/interfaces/issue_resolution_repository.dart';
import '../../core/utils/local_git_repository_fixture.dart';

class Ts127VariedFrontmatterTypesRepositoryFixture {
  Ts127VariedFrontmatterTypesRepositoryFixture._({
    required LocalGitRepositoryFixture repositoryFixture,
    required this.issueService,
  }) : _repositoryFixture = repositoryFixture;

  final LocalGitRepositoryFixture _repositoryFixture;
  final IssueResolutionService issueService;

  static const issueKey = 'DEMO-127';
  static const issueSummary = 'Preserve typed top-level frontmatter values';
  static const issueDescription =
      'Type-safe frontmatter metadata should survive repository resolution.';
  static const issuePath = 'DEMO/DEMO-127/main.md';
  static const myIntFieldKey = 'my_int';
  static const myIntFieldValue = 100;
  static const myBoolFieldKey = 'my_bool';
  static const myBoolFieldValue = false;
  static const myListFieldKey = 'my_list';
  static const myListFieldValue = <String>['a', 'b'];

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts127VariedFrontmatterTypesRepositoryFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-127 Tester',
      userEmail: 'ts127@example.com',
    );
    await _seedRepository(repositoryFixture);
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryFixture.directory.path,
    );

    return Ts127VariedFrontmatterTypesRepositoryFixture._(
      repositoryFixture: repositoryFixture,
      issueService: IssueResolutionService(
        _TrackStateIssueResolutionRepository(repository),
      ),
    );
  }

  static Future<void> _seedRepository(
    LocalGitRepositoryFixture repositoryFixture,
  ) async {
    await repositoryFixture.writeFile(
      'DEMO/project.json',
      '${jsonEncode({'key': 'DEMO', 'name': 'Demo Project'})}\n',
    );
    await repositoryFixture.writeFile(
      'DEMO/config/statuses.json',
      '${jsonEncode([
        {'id': 'closed', 'name': 'Closed'},
      ])}\n',
    );
    await repositoryFixture.writeFile(
      'DEMO/config/issue-types.json',
      '${jsonEncode([
        {'id': 'story', 'name': 'Story'},
      ])}\n',
    );
    await repositoryFixture.writeFile(
      'DEMO/config/fields.json',
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
      ])}\n',
    );
    await repositoryFixture.writeFile(issuePath, '''
---
key: $issueKey
project: DEMO
issueType: story
status: closed
summary: $issueSummary
assignee: qa-user
reporter: qa-admin
$myIntFieldKey: $myIntFieldValue
$myBoolFieldKey: $myBoolFieldValue
$myListFieldKey: ["a", "b"]
updated: 2026-05-09T00:00:00Z
---

# Description

$issueDescription
''');
    await repositoryFixture.stageAll();
    await repositoryFixture.commit('Seed TS-127 fixture');
  }

  Future<IssueResolutionResult> resolveIssueByKey() {
    return issueService.resolveIssueByKey(issueKey);
  }

  Future<void> dispose() async {
    await _repositoryFixture.dispose();
  }
}

class _TrackStateIssueResolutionRepository
    implements IssueResolutionRepository {
  const _TrackStateIssueResolutionRepository(this._repository);

  final LocalTrackStateRepository _repository;

  @override
  Future<TrackerSnapshot> loadSnapshot() {
    return _repository.loadSnapshot();
  }
}
