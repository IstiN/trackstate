import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import '../../../components/services/issue_attachment_metadata_repository_service.dart';
import '../../../core/interfaces/issue_attachment_metadata_loader.dart';

class Ts310AttachmentMetadataFixture {
  Ts310AttachmentMetadataFixture._(this.repositoryDirectory);

  static const issueKey = 'DEMO-1';
  static const issueSummary = 'Attachment metadata contract fixture';
  static const issuePath = 'DEMO/DEMO-1/main.md';
  static const standardAttachmentName = 'architecture-diagram.svg';
  static const lfsAttachmentName = 'release-proof.png';
  static const standardAttachmentPath =
      'DEMO/DEMO-1/attachments/$standardAttachmentName';
  static const lfsAttachmentPath = 'DEMO/DEMO-1/attachments/$lfsAttachmentName';
  static const expectedLfsOid =
      '8f31c1a9a1f7f81d8d4d7f7b77f8de1ad8c8fd4d392376f2c0f1b0c7ecac1057';
  static const expectedLfsSizeBytes = 5242880;

  static const _commitAuthor = 'Attachment Tester';
  static const _commitEmail = 'attachment-tester@example.com';
  static const _commitTimestamp = '2026-05-11T00:00:00Z';
  static const _standardAttachmentSvg = '''
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 60">
  <rect width="120" height="60" fill="#0f172a" rx="8"/>
  <text x="60" y="34" font-size="12" text-anchor="middle" fill="#f8fafc">
    TS-310 attachment contract
  </text>
</svg>
''';
  static const _lfsPointerContent =
      '''
version https://git-lfs.github.com/spec/v1
oid sha256:$expectedLfsOid
size $expectedLfsSizeBytes
''';

  final Directory repositoryDirectory;

  String get repositoryPath => repositoryDirectory.path;

  LocalTrackStateRepository get repository =>
      LocalTrackStateRepository(repositoryPath: repositoryPath);

  IssueAttachmentMetadataLoader get attachmentMetadataLoader =>
      IssueAttachmentMetadataRepositoryService(repository: repository);

  int get expectedStandardSizeBytes =>
      utf8.encode(_standardAttachmentSvg).length;

  Future<String> expectedStandardBlobSha() =>
      _gitOutput(['rev-parse', 'HEAD:$standardAttachmentPath']);

  Future<String> lfsPointerBlobSha() =>
      _gitOutput(['rev-parse', 'HEAD:$lfsAttachmentPath']);

  static Future<Ts310AttachmentMetadataFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'ts310-attachments-',
    );
    final fixture = Ts310AttachmentMetadataFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => repositoryDirectory.delete(recursive: true);

  Future<void> _seedRepository() async {
    await _writeFile(
      '.gitattributes',
      '*.png filter=lfs diff=lfs merge=lfs -text\n',
    );
    await _writeFile(
      'DEMO/project.json',
      '{"key":"DEMO","name":"Attachment Metadata Demo"}\n',
    );
    await _writeFile(
      'DEMO/config/statuses.json',
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]\n',
    );
    await _writeFile('DEMO/config/issue-types.json', '[{"name":"Story"}]\n');
    await _writeFile('DEMO/config/fields.json', '[{"name":"Summary"}]\n');
    await _writeFile(issuePath, '''
---
key: $issueKey
project: DEMO
issueType: Story
status: In Progress
priority: High
summary: $issueSummary
assignee: attachment-user
reporter: attachment-user
updated: $_commitTimestamp
---

# Description

Fixture for verifying attachment metadata contracts.
''');
    await _writeFile(standardAttachmentPath, _standardAttachmentSvg);
    await _writeFile(lfsAttachmentPath, _lfsPointerContent);

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', _commitAuthor]);
    await _git(['config', '--local', 'user.email', _commitEmail]);
    await _git(['add', '.']);
    await _git(
      ['commit', '-m', 'Seed TS-310 attachment metadata fixture'],
      environment: <String, String>{
        'GIT_AUTHOR_NAME': _commitAuthor,
        'GIT_AUTHOR_EMAIL': _commitEmail,
        'GIT_AUTHOR_DATE': _commitTimestamp,
        'GIT_COMMITTER_NAME': _commitAuthor,
        'GIT_COMMITTER_EMAIL': _commitEmail,
        'GIT_COMMITTER_DATE': _commitTimestamp,
      },
    );
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('$repositoryPath/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(
    List<String> args, {
    Map<String, String> environment = const <String, String>{},
  }) async {
    final result = await Process.run('git', <String>[
      '-C',
      repositoryPath,
      ...args,
    ], environment: environment.isEmpty ? null : environment);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }

  Future<String> _gitOutput(List<String> args) async {
    final result = await Process.run('git', <String>[
      '-C',
      repositoryPath,
      ...args,
    ]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result.stdout.toString().trim();
  }
}
