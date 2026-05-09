import 'dart:convert';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/issue_resolution_service.dart';
import '../../core/interfaces/issue_resolution_repository.dart';
import '../../core/utils/local_git_repository_fixture.dart';

class Ts96UnmappedFrontmatterRepositoryFixture {
  Ts96UnmappedFrontmatterRepositoryFixture._({
    required LocalGitRepositoryFixture repositoryFixture,
    required this.issueService,
  }) : _repositoryFixture = repositoryFixture;

  final LocalGitRepositoryFixture _repositoryFixture;
  final IssueResolutionService issueService;

  static const issueKey = 'DEMO-96';
  static const issuePath = 'DEMO/DEMO-96/main.md';
  static const unmappedFieldKey = 'unmapped_field';
  static const unmappedFieldValue = 'some_data';

  static Future<Ts96UnmappedFrontmatterRepositoryFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-96 Tester',
      userEmail: 'ts96@example.com',
    );
    await _seedRepository(repositoryFixture);
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryFixture.directory.path,
    );

    return Ts96UnmappedFrontmatterRepositoryFixture._(
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
        {'id': 'priority', 'name': 'Priority', 'type': 'option', 'required': false},
      ])}\n',
    );
    await repositoryFixture.writeFile(
      'DEMO/config/priorities.json',
      '${jsonEncode([
        {'id': 'high', 'name': 'High'},
      ])}\n',
    );
    await repositoryFixture.writeFile(issuePath, '''
---
key: $issueKey
project: DEMO
issueType: story
status: done
priority: high
summary: Preserve non-core frontmatter keys
assignee: qa-user
reporter: qa-admin
created: 2026-05-08T23:59:59Z
$unmappedFieldKey: $unmappedFieldValue
updated: 2026-05-09T00:00:00Z
---

# Description

Created from arbitrary frontmatter metadata.
''');
    await repositoryFixture.stageAll();
    await repositoryFixture.commit('Seed TS-96 fixture');
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
