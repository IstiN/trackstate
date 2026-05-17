import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

void main() {
  test(
    'repository snapshot synthesizes inverse symmetric links for target issues',
    () async {
      final repo = await _createInverseLinkRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final snapshot = await repository.loadSnapshot();
      final targetIssue = snapshot.issues.firstWhere(
        (issue) => issue.key == 'DEMO-10',
      );

      expect(targetIssue.links, hasLength(1));
      expect(targetIssue.links.single.type, 'relates to');
      expect(targetIssue.links.single.targetKey, 'DEMO-2');
      expect(targetIssue.links.single.direction, 'inward');
    },
  );
}

Future<Directory> _createInverseLinkRepository() async {
  final directory = await Directory.systemTemp.createTemp(
    'trackstate-inverse-links-',
  );
  await _writeFile(
    directory,
    'DEMO/project.json',
    '{"key":"DEMO","name":"Inverse Link Demo"}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/statuses.json',
    '${jsonEncode([
      {'id': 'todo', 'name': 'To Do'},
      {'id': 'in-progress', 'name': 'In Progress'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/issue-types.json',
    '${jsonEncode([
      {'id': 'epic', 'name': 'Epic'},
      {'id': 'story', 'name': 'Story'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/fields.json',
    '${jsonEncode([
      {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
      {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
    ])}\n',
  );
  await _writeFile(
    directory,
    'DEMO/config/priorities.json',
    '${jsonEncode([
      {'id': 'medium', 'name': 'Medium'},
      {'id': 'high', 'name': 'High'},
    ])}\n',
  );
  await _writeFile(directory, 'DEMO/.trackstate/index/tombstones.json', '[]\n');
  await _writeFile(directory, 'DEMO/DEMO-1/main.md', '''
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

Root epic for inverse link hydration tests.
''');
  await _writeFile(directory, 'DEMO/DEMO-1/DEMO-2/main.md', '''
---
key: DEMO-2
project: DEMO
issueType: story
status: in-progress
priority: medium
summary: Source story
assignee: demo-user
reporter: demo-admin
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Summary

Source story

# Description

Stores the canonical outward symmetric link.
''');
  await _writeFile(
    directory,
    'DEMO/DEMO-1/DEMO-2/links.json',
    '${jsonEncode([
      {'type': 'relates-to', 'target': 'DEMO-10', 'direction': 'outward'},
    ])}\n',
  );
  await _writeFile(directory, 'DEMO/DEMO-10/main.md', '''
---
key: DEMO-10
project: DEMO
issueType: epic
status: todo
priority: medium
summary: Target epic
assignee: demo-admin
reporter: demo-admin
updated: 2026-05-05T00:10:00Z
---

# Summary

Target epic

# Description

Receives the synthesized inward symmetric link.
''');

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
  await _git(directory.path, ['commit', '-m', 'Initial inverse link fixture']);
  return directory;
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
