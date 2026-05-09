import 'dart:convert';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/issue_resolution_service.dart';
import '../../core/interfaces/issue_resolution_repository.dart';
import '../../core/utils/local_git_repository_fixture.dart';

class Ts126MergedCustomFieldsRepositoryFixture {
  Ts126MergedCustomFieldsRepositoryFixture._({
    required LocalGitRepositoryFixture repositoryFixture,
    required this.issueService,
  }) : _repositoryFixture = repositoryFixture;

  final LocalGitRepositoryFixture _repositoryFixture;
  final IssueResolutionService issueService;

  static const issueKey = 'DEMO-126';
  static const issuePath = 'DEMO/DEMO-126/main.md';
  static const issueSummary = 'Merged explicit and arbitrary custom fields';
  static const issueDescription =
      'The issue preserves explicit customFields entries and arbitrary '
      'top-level frontmatter keys together.';
  static const explicitCustomFieldKey = 'explicit_key';
  static const explicitCustomFieldValue = 'value1';
  static const arbitraryCustomFieldKey = 'arbitrary_key';
  static const arbitraryCustomFieldValue = 'value2';

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts126MergedCustomFieldsRepositoryFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: 'TS-126 Tester',
      userEmail: 'ts126@example.com',
    );
    await _seedRepository(repositoryFixture);
    final repository = LocalTrackStateRepository(
      repositoryPath: repositoryFixture.directory.path,
    );

    return Ts126MergedCustomFieldsRepositoryFixture._(
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
        {'id': 'high', 'name': 'High'},
      ])}\n',
    );
    await repositoryFixture.writeFile(issuePath, '''
---
key: $issueKey
project: DEMO
issueType: story
status: open
priority: high
summary: $issueSummary
assignee: qa-user
reporter: qa-admin
customFields:
  $explicitCustomFieldKey: "$explicitCustomFieldValue"
$arbitraryCustomFieldKey: "$arbitraryCustomFieldValue"
updated: 2026-05-09T00:00:00Z
---

# Description

$issueDescription
''');
    await repositoryFixture.stageAll();
    await repositoryFixture.commit('Seed TS-126 fixture');
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
