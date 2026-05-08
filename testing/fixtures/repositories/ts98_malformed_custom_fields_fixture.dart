import 'dart:convert';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/issue_resolution_service.dart';
import '../../core/interfaces/issue_resolution_repository.dart';
import '../../core/utils/local_git_repository_fixture.dart';

class Ts98MalformedCustomFieldsFixture {
  Ts98MalformedCustomFieldsFixture._({
    required LocalGitRepositoryFixture repositoryFixture,
    required this.issueService,
  }) : _repositoryFixture = repositoryFixture;

  final LocalGitRepositoryFixture _repositoryFixture;
  final IssueResolutionService issueService;

  static const issueKey = 'DEMO-98';
  static const issueSummary = 'Malformed customFields frontmatter issue';
  static const issueDescription =
      'The issue still loads when customFields uses a string value.';
  static const invalidCustomFieldsValue = 'invalid_string_value';
  static const issuePath = 'DEMO/DEMO-98/main.md';

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts98MalformedCustomFieldsFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-98 Tester',
      userEmail: 'ts98@example.com',
    );
    await _seedRepository(repositoryFixture);
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryFixture.directory.path,
    );

    return Ts98MalformedCustomFieldsFixture._(
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
        {'id': 'todo', 'name': 'To Do'},
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
        {'id': 'field_101', 'name': 'Custom Field 101', 'type': 'string', 'required': false},
        {'id': 'priority', 'name': 'Priority', 'type': 'option', 'required': false},
      ])}\n',
    );
    await repositoryFixture.writeFile(
      'DEMO/config/priorities.json',
      '${jsonEncode([
        {'id': 'low', 'name': 'Low'},
      ])}\n',
    );
    await repositoryFixture.writeFile(issuePath, '''
---
key: $issueKey
project: DEMO
issueType: story
status: todo
priority: low
summary: $issueSummary
assignee: qa-user
reporter: qa-admin
customFields: "$invalidCustomFieldsValue"
updated: 2026-05-08T00:00:00Z
---

# Description

$issueDescription
''');
    await repositoryFixture.stageAll();
    await repositoryFixture.commit('Seed TS-98 fixture');
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
