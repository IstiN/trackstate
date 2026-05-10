import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/issue_mutation_service.dart';
import 'package:trackstate/domain/models/issue_mutation_models.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

void main() {
  test(
    'service creates a nested issue under the canonical epic path',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.createIssue(
        summary: 'Nested under epic',
        description: 'Created through the shared mutation service.',
        epicKey: 'DEMO-10',
        fields: const {'storyPoints': 5},
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.storagePath, 'DEMO/DEMO-10/DEMO-11/main.md');
      expect(result.value!.epicKey, 'DEMO-10');
      expect(
        File('${repo.path}/DEMO/DEMO-10/DEMO-11/main.md').existsSync(),
        isTrue,
      );
      expect(
        File(
          '${repo.path}/DEMO/.trackstate/index/issues.json',
        ).readAsStringSync(),
        contains('DEMO-11'),
      );
    },
  );

  test(
    'service updates fields and acceptance criteria in one mutation',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.updateFields(
        issueKey: 'DEMO-2',
        fields: const {
          'summary': 'Updated nested story',
          'description': 'Updated through the mutation service.',
          'storyPoints': 13,
          'acceptanceCriteria': ['Keeps markdown-backed acceptance criteria.'],
        },
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.summary, 'Updated nested story');
      expect(
        result.value!.description,
        'Updated through the mutation service.',
      );
      expect(result.value!.customFields['storyPoints'], 13);
      expect(
        File(
          '${repo.path}/DEMO/DEMO-1/DEMO-2/acceptance_criteria.md',
        ).readAsStringSync(),
        '- Keeps markdown-backed acceptance criteria.\n',
      );
    },
  );

  test(
    'service enforces workflow transitions and auto-defaults done resolution',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.transitionIssue(
        issueKey: 'DEMO-2',
        status: 'Done',
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.statusId, 'done');
      expect(result.value!.resolutionId, 'done');
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/main.md').readAsStringSync(),
        contains('resolution: done'),
      );
    },
  );

  test(
    'service rejects workflow transitions that are not configured',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.transitionIssue(
        issueKey: 'DEMO-3',
        status: 'Done',
      );

      expect(result.isSuccess, isFalse);
      expect(result.failure!.category, IssueMutationErrorCategory.validation);
      expect(result.failure!.message, contains('Workflow does not allow'));
    },
  );

  test(
    'service reassigns an issue by moving its subtree to the new epic path',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.reassignIssue(
        issueKey: 'DEMO-2',
        epicKey: 'DEMO-10',
      );

      expect(result.isSuccess, isTrue);
      expect(result.value!.storagePath, 'DEMO/DEMO-10/DEMO-2/main.md');
      expect(result.value!.epicKey, 'DEMO-10');
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/main.md').existsSync(),
        isFalse,
      );
      expect(
        File('${repo.path}/DEMO/DEMO-10/DEMO-2/main.md').existsSync(),
        isTrue,
      );
      expect(
        File(
          '${repo.path}/DEMO/DEMO-10/DEMO-2/DEMO-3/main.md',
        ).readAsStringSync(),
        contains('epic: DEMO-10'),
      );
    },
  );

  test(
    'service normalizes inverse link labels to one stored canonical link',
    () async {
      final repo = await _createMutationRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      await repository.loadSnapshot();
      await repository.connect(
        const RepositoryConnection(repository: '.', branch: 'main', token: ''),
      );
      final service = IssueMutationService(repository: repository);

      final result = await service.createLink(
        issueKey: 'DEMO-2',
        targetKey: 'DEMO-10',
        type: 'is blocked by',
      );

      expect(result.isSuccess, isTrue);
      final links =
          jsonDecode(
                File(
                  '${repo.path}/DEMO/DEMO-1/DEMO-2/links.json',
                ).readAsStringSync(),
              )
              as List<dynamic>;
      expect(links, hasLength(1));
      expect(links.single['type'], 'blocks');
      expect(links.single['direction'], 'inward');
      expect(links.single['target'], 'DEMO-10');
    },
  );

  test('service archives issues through the shared typed contract', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.archiveIssue('DEMO-10');

    expect(result.isSuccess, isTrue);
    expect(result.value!.isArchived, isTrue);
    expect(
      File(
        '${repo.path}/DEMO/.trackstate/archive/DEMO-10/main.md',
      ).existsSync(),
      isTrue,
    );
  });

  test('service blocks delete when child issues would be orphaned', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.deleteIssue('DEMO-1');

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.validation);
    expect(result.failure!.message, contains('still has child issues'));
  });

  test('service returns a typed dirty-worktree failure', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    await _writeFile(
      repo,
      'DEMO/DEMO-1/main.md',
      '${File('${repo.path}/DEMO/DEMO-1/main.md').readAsStringSync()}\nDirty.\n',
    );

    final result = await service.createIssue(
      summary: 'Blocked create',
      description: 'Should fail with a dirty-worktree category.',
    );

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.dirtyWorktree);
  });

  test('service rejects non-epic explicit epic targets', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.createIssue(
      summary: 'Invalid hierarchy',
      epicKey: 'DEMO-2',
    );

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.validation);
    expect(result.failure!.message, contains('must reference an epic issue'));
  });

  test('service rejects assigning epics into another hierarchy', () async {
    final repo = await _createMutationRepository();
    addTearDown(() => repo.delete(recursive: true));

    final repository = LocalTrackStateRepository(repositoryPath: repo.path);
    await repository.loadSnapshot();
    await repository.connect(
      const RepositoryConnection(repository: '.', branch: 'main', token: ''),
    );
    final service = IssueMutationService(repository: repository);

    final result = await service.reassignIssue(
      issueKey: 'DEMO-10',
      epicKey: 'DEMO-1',
    );

    expect(result.isSuccess, isFalse);
    expect(result.failure!.category, IssueMutationErrorCategory.validation);
    expect(result.failure!.message, contains('Epic issues cannot belong'));
  });

  test(
    'service creates and reassigns issues through the hosted GitHub provider',
    () async {
      final harness = await _createHostedMutationHarness();
      final service = harness.service;
      final backend = harness.backend;

      final created = await service.createIssue(
        summary: 'Hosted nested issue',
        description: 'Created through the GitHub-backed mutation path.',
        epicKey: 'DEMO-10',
      );

      expect(created.isSuccess, isTrue);
      expect(created.value!.storagePath, 'DEMO/DEMO-10/DEMO-11/main.md');
      expect(backend.exists('DEMO/DEMO-10/DEMO-11/main.md'), isTrue);
      expect(
        backend.readText('DEMO/.trackstate/index/issues.json'),
        contains('DEMO-11'),
      );

      final moved = await service.reassignIssue(
        issueKey: 'DEMO-2',
        epicKey: 'DEMO-10',
      );

      expect(moved.isSuccess, isTrue);
      expect(moved.value!.storagePath, 'DEMO/DEMO-10/DEMO-2/main.md');
      expect(backend.exists('DEMO/DEMO-1/DEMO-2/main.md'), isFalse);
      expect(backend.exists('DEMO/DEMO-10/DEMO-2/main.md'), isTrue);
      expect(
        backend.readText('DEMO/DEMO-10/DEMO-2/DEMO-3/main.md'),
        contains('epic: DEMO-10'),
      );
    },
  );

  test('service archives issues through the hosted GitHub provider', () async {
    final harness = await _createHostedMutationHarness();
    final result = await harness.service.archiveIssue('DEMO-10');

    expect(result.isSuccess, isTrue);
    expect(
      harness.backend.exists('DEMO/.trackstate/archive/DEMO-10/main.md'),
      isTrue,
    );
    expect(harness.backend.exists('DEMO/DEMO-10/main.md'), isFalse);
  });

  test('service deletes issues through the hosted GitHub provider', () async {
    final harness = await _createHostedMutationHarness();
    final result = await harness.service.deleteIssue('DEMO-10');

    expect(result.isSuccess, isTrue);
    expect(harness.backend.exists('DEMO/DEMO-10/main.md'), isFalse);
    expect(
      harness.backend.readText('DEMO/.trackstate/index/tombstones.json'),
      contains('DEMO-10'),
    );
    expect(
      harness.backend.exists('DEMO/.trackstate/tombstones/DEMO-10.json'),
      isTrue,
    );
  });
}

Future<Directory> _createMutationRepository() async {
  final directory = await Directory.systemTemp.createTemp(
    'trackstate-mutation-',
  );
  for (final entry in _mutationFixtureFiles().entries) {
    await _writeFile(directory, entry.key, entry.value);
  }

  await _git(directory.path, ['init', '-b', 'main']);
  await _git(directory.path, [
    'config',
    '--local',
    'user.name',
    'Local Tester',
  ]);
  await _git(directory.path, [
    'config',
    '--local',
    'user.email',
    'local@example.com',
  ]);
  await _git(directory.path, ['add', '.']);
  await _git(directory.path, ['commit', '-m', 'Initial mutation fixture']);
  return directory;
}

Map<String, String> _mutationFixtureFiles() => {
  'DEMO/project.json': '{"key":"DEMO","name":"Mutation Demo"}\n',
  'DEMO/config/statuses.json':
      '${jsonEncode([
        {'id': 'todo', 'name': 'To Do'},
        {'id': 'in-progress', 'name': 'In Progress'},
        {'id': 'in-review', 'name': 'In Review'},
        {'id': 'done', 'name': 'Done'},
      ])}\n',
  'DEMO/config/issue-types.json':
      '${jsonEncode([
        {'id': 'epic', 'name': 'Epic'},
        {'id': 'story', 'name': 'Story'},
        {'id': 'subtask', 'name': 'Sub-task'},
      ])}\n',
  'DEMO/config/fields.json':
      '${jsonEncode([
        {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
        {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
      ])}\n',
  'DEMO/config/priorities.json':
      '${jsonEncode([
        {'id': 'medium', 'name': 'Medium'},
        {'id': 'high', 'name': 'High'},
      ])}\n',
  'DEMO/config/resolutions.json': '[{"id":"done","name":"Done"}]\n',
  'DEMO/config/workflows.json':
      '${jsonEncode({
        'default': {
          'statuses': ['To Do', 'In Progress', 'In Review', 'Done'],
          'transitions': [
            {'id': 'start', 'name': 'Start work', 'from': 'To Do', 'to': 'In Progress'},
            {'id': 'review', 'name': 'Request review', 'from': 'In Progress', 'to': 'In Review'},
            {'id': 'complete', 'name': 'Complete', 'from': 'In Review', 'to': 'Done'},
            {'id': 'reopen', 'name': 'Reopen', 'from': 'Done', 'to': 'To Do'},
          ],
        },
      })}\n',
  'DEMO/.trackstate/index/issues.json':
      '${jsonEncode([
        {
          'key': 'DEMO-1',
          'path': 'DEMO/DEMO-1/main.md',
          'parent': null,
          'epic': null,
          'children': ['DEMO-2'],
          'archived': false,
        },
        {
          'key': 'DEMO-2',
          'path': 'DEMO/DEMO-1/DEMO-2/main.md',
          'parent': null,
          'epic': 'DEMO-1',
          'children': ['DEMO-3'],
          'archived': false,
        },
        {'key': 'DEMO-3', 'path': 'DEMO/DEMO-1/DEMO-2/DEMO-3/main.md', 'parent': 'DEMO-2', 'epic': 'DEMO-1', 'children': [], 'archived': false},
        {'key': 'DEMO-10', 'path': 'DEMO/DEMO-10/main.md', 'parent': null, 'epic': null, 'children': [], 'archived': false},
      ])}\n',
  'DEMO/.trackstate/index/tombstones.json': '[]\n',
  'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: epic
status: in-progress
priority: high
summary: Platform epic
assignee: demo-admin
reporter: demo-admin
updated: 2026-05-05T00:00:00Z
---

# Summary

Platform epic

# Description

Root epic for lifecycle tests.
''',
  'DEMO/DEMO-1/DEMO-2/main.md': '''
---
key: DEMO-2
project: DEMO
issueType: story
status: in-review
priority: medium
summary: Nested story
assignee: demo-user
reporter: demo-admin
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Summary

Nested story

# Description

Story ready for workflow and hierarchy tests.
''',
  'DEMO/DEMO-1/DEMO-2/DEMO-3/main.md': '''
---
key: DEMO-3
project: DEMO
issueType: subtask
status: todo
priority: medium
summary: Nested sub-task
assignee: demo-user
reporter: demo-admin
parent: DEMO-2
epic: DEMO-1
updated: 2026-05-05T00:10:00Z
---

# Summary

Nested sub-task

# Description

Sub-task used to verify subtree moves.
''',
  'DEMO/DEMO-10/main.md': '''
---
key: DEMO-10
project: DEMO
issueType: epic
status: todo
priority: medium
summary: Alternative epic
assignee: demo-admin
reporter: demo-admin
updated: 2026-05-05T00:15:00Z
---

# Summary

Alternative epic

# Description

Second epic used as a move target.
''',
  '.gitattributes': '*.png filter=lfs diff=lfs merge=lfs -text\n',
};

Future<_HostedMutationHarness> _createHostedMutationHarness() async {
  final backend = _HostedRepositoryBackend(files: _mutationFixtureFiles());
  final repository = SetupTrackStateRepository(client: backend.client);
  await repository.loadSnapshot();
  await repository.connect(
    const RepositoryConnection(
      repository: SetupTrackStateRepository.repositoryName,
      branch: 'main',
      token: 'token',
    ),
  );
  return _HostedMutationHarness(
    backend: backend,
    service: IssueMutationService(repository: repository),
  );
}

Future<void> _writeFile(
  Directory root,
  String relativePath,
  String content,
) async {
  final file = File('${root.path}/$relativePath');
  await file.parent.create(recursive: true);
  await file.writeAsString(content);
}

Future<void> _git(String repositoryPath, List<String> args) async {
  final result = await Process.run('git', ['-C', repositoryPath, ...args]);
  if (result.exitCode != 0) {
    throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
  }
}

class _HostedMutationHarness {
  const _HostedMutationHarness({required this.backend, required this.service});

  final _HostedRepositoryBackend backend;
  final IssueMutationService service;
}

class _HostedRepositoryBackend {
  _HostedRepositoryBackend({required Map<String, String> files})
    : _files = {
        for (final entry in files.entries)
          entry.key: Uint8List.fromList(utf8.encode(entry.value)),
      } {
    final initialSnapshot = _copyFiles(_files);
    final initialTreeSha = _nextSha('tree');
    _treeSnapshots[initialTreeSha] = initialSnapshot;
    _headCommitSha = _nextSha('commit');
    _commitSnapshots[_headCommitSha] = _copyFiles(initialSnapshot);
    _commitTrees[_headCommitSha] = initialTreeSha;
  }

  static const _repository = SetupTrackStateRepository.repositoryName;

  final Map<String, Uint8List> _files;
  final Map<String, Uint8List> _blobStore = <String, Uint8List>{};
  final Map<String, Map<String, Uint8List>> _treeSnapshots =
      <String, Map<String, Uint8List>>{};
  final Map<String, Map<String, Uint8List>> _commitSnapshots =
      <String, Map<String, Uint8List>>{};
  final Map<String, String> _commitTrees = <String, String>{};
  int _shaCounter = 0;
  late String _headCommitSha;

  late final http.Client client = MockClient(_handle);

  bool exists(String path) => _files.containsKey(path);

  String readText(String path) => utf8.decode(_files[path]!);

  Future<http.Response> _handle(http.Request request) async {
    final path = request.url.path;
    if (path == '/repos/$_repository' && request.method == 'GET') {
      return http.Response(
        '{"permissions":{"pull":true,"push":true,"admin":false}}',
        200,
      );
    }
    if (path == '/user' && request.method == 'GET') {
      return http.Response('{"login":"octocat","name":"Mona"}', 200);
    }
    if (path == '/repos/$_repository/git/trees/main' &&
        request.method == 'GET') {
      final tree = _files.keys.toList()..sort();
      return http.Response(
        jsonEncode({
          'tree': [
            for (final filePath in tree) {'path': filePath, 'type': 'blob'},
          ],
        }),
        200,
      );
    }
    if (path == '/repos/$_repository/git/ref/heads/main' &&
        request.method == 'GET') {
      return http.Response(
        jsonEncode({
          'ref': 'refs/heads/main',
          'object': {'sha': _headCommitSha},
        }),
        200,
      );
    }
    if (path.startsWith('/repos/$_repository/git/commits/') &&
        request.method == 'GET') {
      final commitSha = path.split('/').last;
      final treeSha = _commitTrees[commitSha];
      if (treeSha == null) {
        return http.Response('{"message":"Not Found"}', 404);
      }
      return http.Response(
        jsonEncode({
          'sha': commitSha,
          'tree': {'sha': treeSha},
        }),
        200,
      );
    }
    if (path == '/repos/$_repository/git/blobs' && request.method == 'POST') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final encoding = body['encoding']?.toString();
      final content = body['content']?.toString() ?? '';
      final bytes = encoding == 'base64'
          ? Uint8List.fromList(base64Decode(content))
          : Uint8List.fromList(utf8.encode(content));
      final sha = _nextSha('blob');
      _blobStore[sha] = bytes;
      return http.Response(jsonEncode({'sha': sha}), 201);
    }
    if (path == '/repos/$_repository/git/trees' && request.method == 'POST') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final baseTreeSha = body['base_tree']?.toString();
      final baseSnapshot = _copyFiles(_treeSnapshots[baseTreeSha] ?? _files);
      final rawTree = body['tree'];
      if (rawTree is List) {
        for (final rawEntry in rawTree.whereType<Map<String, Object?>>()) {
          final filePath = rawEntry['path']?.toString() ?? '';
          if (filePath.isEmpty) {
            continue;
          }
          if (rawEntry.containsKey('sha') && rawEntry['sha'] == null) {
            baseSnapshot.remove(filePath);
            continue;
          }
          if (rawEntry['content'] != null) {
            baseSnapshot[filePath] = Uint8List.fromList(
              utf8.encode(rawEntry['content']!.toString()),
            );
            continue;
          }
          final blobSha = rawEntry['sha']?.toString();
          final blob = blobSha == null ? null : _blobStore[blobSha];
          if (blob == null) {
            return http.Response('{"message":"Unknown blob"}', 422);
          }
          baseSnapshot[filePath] = Uint8List.fromList(blob);
        }
      }
      final treeSha = _nextSha('tree');
      _treeSnapshots[treeSha] = baseSnapshot;
      return http.Response(jsonEncode({'sha': treeSha}), 201);
    }
    if (path == '/repos/$_repository/git/commits' && request.method == 'POST') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final treeSha = body['tree']?.toString();
      final snapshot = treeSha == null ? null : _treeSnapshots[treeSha];
      if (snapshot == null) {
        return http.Response('{"message":"Unknown tree"}', 422);
      }
      final commitSha = _nextSha('commit');
      _commitSnapshots[commitSha] = _copyFiles(snapshot);
      _commitTrees[commitSha] = treeSha!;
      return http.Response(jsonEncode({'sha': commitSha}), 201);
    }
    if (path == '/repos/$_repository/git/refs/heads/main' &&
        request.method == 'PATCH') {
      final body = jsonDecode(request.body) as Map<String, Object?>;
      final commitSha = body['sha']?.toString();
      final snapshot = commitSha == null ? null : _commitSnapshots[commitSha];
      if (snapshot == null) {
        return http.Response('{"message":"Unknown commit"}', 422);
      }
      _headCommitSha = commitSha!;
      _files
        ..clear()
        ..addAll(_copyFiles(snapshot));
      return http.Response(
        jsonEncode({
          'ref': 'refs/heads/main',
          'object': {'sha': commitSha},
        }),
        200,
      );
    }

    final contentsPrefix = '/repos/$_repository/contents/';
    if (path.startsWith(contentsPrefix) && request.method == 'GET') {
      final filePath = path.substring(contentsPrefix.length);
      final bytes = _files[filePath];
      if (bytes == null) {
        return http.Response('{"message":"Not Found"}', 404);
      }
      return _contentResponse(bytes);
    }

    return http.Response('{"message":"Unhandled"}', 404);
  }

  Map<String, Uint8List> _copyFiles(Map<String, Uint8List> source) => {
    for (final entry in source.entries)
      entry.key: Uint8List.fromList(entry.value),
  };

  String _nextSha(String prefix) {
    _shaCounter++;
    final seed = '$prefix-$_shaCounter'.codeUnits;
    var value = 1469598103934665603;
    for (final unit in seed) {
      value ^= unit;
      value = (value * 1099511628211) & 0xffffffffffffffff;
    }
    final chunk = value.toRadixString(16).padLeft(16, '0');
    return List.filled(3, chunk).join().substring(0, 40);
  }

  http.Response _contentResponse(Uint8List bytes) {
    final encoded = base64Encode(bytes);
    return http.Response(
      jsonEncode({'content': encoded, 'sha': _blobRevision(bytes)}),
      200,
    );
  }

  String _blobRevision(Uint8List bytes) {
    var value = 2166136261;
    for (final byte in bytes) {
      value ^= byte;
      value = (value * 16777619) & 0xffffffff;
    }
    final chunk = value.toRadixString(16).padLeft(8, '0');
    return List.filled(5, chunk).join().substring(0, 40);
  }
}
