import 'dart:convert';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/issue_resolution_service.dart';
import '../../core/interfaces/issue_resolution_repository.dart';
import '../../core/utils/local_git_repository_fixture.dart';

class Ts128NullOrEmptyFrontmatterRepositoryFixture {
  Ts128NullOrEmptyFrontmatterRepositoryFixture._({
    required LocalGitRepositoryFixture repositoryFixture,
    required this.issueService,
  }) : _repositoryFixture = repositoryFixture;

  final LocalGitRepositoryFixture _repositoryFixture;
  final IssueResolutionService issueService;

  static const issueKey = 'DEMO-128';
  static const issuePath = 'DEMO/DEMO-128/main.md';
  static const issueSummary =
      'Preserve null and empty arbitrary frontmatter keys';
  static const issueDescription =
      'Null and empty arbitrary frontmatter keys stay available to clients.';
  static const emptyCustomFieldKey = 'empty_key';
  static const nullCustomFieldKey = 'null_key';

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts128NullOrEmptyFrontmatterRepositoryFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-128 Tester',
      userEmail: 'ts128@example.com',
    );
    await _seedRepository(repositoryFixture);
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryFixture.directory.path,
    );

    return Ts128NullOrEmptyFrontmatterRepositoryFixture._(
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
        {'id': 'open', 'name': 'Open'},
        {'id': 'done', 'name': 'Done'},
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
        {'id': 'priority', 'name': 'Priority', 'type': 'option', 'required': false},
      ])}\n',
    );
    await repositoryFixture.writeFile(
      'DEMO/config/priorities.json',
      '${jsonEncode([
        {'id': 'medium', 'name': 'Medium'},
      ])}\n',
    );
    await repositoryFixture.writeFile(issuePath, '''
---
key: $issueKey
project: DEMO
issueType: story
status: open
priority: medium
summary: $issueSummary
assignee: qa-user
reporter: qa-admin
$emptyCustomFieldKey:
$nullCustomFieldKey: null
---

# Description

$issueDescription
''');
    await repositoryFixture.stageAll();
    await repositoryFixture.commit('Seed TS-128 fixture');
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
