import 'dart:io';

import '../../../core/utils/local_git_repository_fixture.dart';

class Ts309LocalGitFixture {
  Ts309LocalGitFixture._(this._repositoryFixture);

  static const issueKey = 'PROJECT-1';
  static const issueSummary = 'Normalize audit history from Git commits';
  static const issuePath = 'PROJECT/PROJECT-1/main.md';
  static const historyMarkdownPath = 'PROJECT/PROJECT-1/history.md';
  static const createdAuthor = 'Creation QA';
  static const descriptionAuthor = 'Description QA';
  static const statusAuthor = 'Status QA';
  static const createdTimestamp = '2026-05-11T00:00:00Z';
  static const descriptionTimestamp = '2026-05-11T00:10:00Z';
  static const statusTimestamp = '2026-05-11T00:20:00Z';
  static const initialDescription =
      'Original description captured when PROJECT-1 was created.';
  static const updatedDescription =
      'Updated description after the repository API edit commit.';

  final LocalGitRepositoryFixture _repositoryFixture;
  late final String creationCommitSha;
  late final String descriptionCommitSha;
  late final String statusCommitSha;

  String get repositoryPath => _repositoryFixture.directory.path;

  static Future<Ts309LocalGitFixture> create() async {
    final repositoryFixture = await LocalGitRepositoryFixture.create(
      userName: createdAuthor,
      userEmail: 'creation.qa@example.com',
    );
    final fixture = Ts309LocalGitFixture._(repositoryFixture);
    await fixture._seedProjectRepository();
    return fixture;
  }

  Future<void> dispose() => _repositoryFixture.dispose();

  Future<String> headRevision() => _gitOutput(['rev-parse', 'HEAD']);

  Future<List<String>> worktreeStatusLines() async {
    final output = await _gitOutput(['status', '--short']);
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<bool> repositoryPathExists(String relativePath) =>
      File('$repositoryPath/$relativePath').exists();

  Future<void> _seedProjectRepository() async {
    final demoDirectory = Directory('${repositoryPath}/DEMO');
    if (await demoDirectory.exists()) {
      await demoDirectory.delete(recursive: true);
    }

    await _repositoryFixture.configureAuthor(
      userName: createdAuthor,
      userEmail: 'creation.qa@example.com',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/project.json',
      '{"key":"PROJECT","name":"Project audit history"}\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/statuses.json',
      '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/issue-types.json',
      '[{"id":"story","name":"Story"}]\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/fields.json',
      '[{"id":"summary","name":"Summary","type":"string","required":true},{"id":"priority","name":"Priority","type":"option","required":false}]\n',
    );
    await _repositoryFixture.writeFile(
      'PROJECT/config/priorities.json',
      '[{"id":"high","name":"High"},{"id":"medium","name":"Medium"}]\n',
    );
    await _repositoryFixture.writeFile(
      issuePath,
      _issueMarkdown(
        status: 'todo',
        updated: createdTimestamp,
        description: initialDescription,
      ),
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit(
      'Create PROJECT-1',
      authorDate: createdTimestamp,
      committerDate: createdTimestamp,
    );
    creationCommitSha = await headRevision();

    await _repositoryFixture.configureAuthor(
      userName: descriptionAuthor,
      userEmail: 'description.qa@example.com',
    );
    await _repositoryFixture.writeFile(
      issuePath,
      _issueMarkdown(
        status: 'todo',
        updated: descriptionTimestamp,
        description: updatedDescription,
      ),
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit(
      'Update PROJECT-1 description',
      authorDate: descriptionTimestamp,
      committerDate: descriptionTimestamp,
    );
    descriptionCommitSha = await headRevision();

    await _repositoryFixture.configureAuthor(
      userName: statusAuthor,
      userEmail: 'status.qa@example.com',
    );
    await _repositoryFixture.writeFile(
      issuePath,
      _issueMarkdown(
        status: 'done',
        updated: statusTimestamp,
        description: updatedDescription,
      ),
    );
    await _repositoryFixture.stageAll();
    await _repositoryFixture.commit(
      'Move PROJECT-1 to Done',
      authorDate: statusTimestamp,
      committerDate: statusTimestamp,
    );
    statusCommitSha = await headRevision();
  }

  String _issueMarkdown({
    required String status,
    required String updated,
    required String description,
  }) {
    return '''
---
key: $issueKey
project: PROJECT
issueType: story
status: $status
priority: high
summary: "$issueSummary"
assignee: ts309-user
reporter: ts309-user
updated: $updated
---

# Description

$description
''';
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', ['-C', repositoryPath, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
