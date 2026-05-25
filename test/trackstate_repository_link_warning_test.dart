import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

void main() {
  test(
    'repository loading logs a warning for non-canonical link metadata',
    () async {
      final repo = await _createRepository();
      addTearDown(() => repo.delete(recursive: true));

      final repository = LocalTrackStateRepository(repositoryPath: repo.path);
      final messages = <String>[];

      final snapshot = await runZoned(
        () => repository.loadSnapshot(),
        zoneSpecification: ZoneSpecification(
          print: (self, parent, zone, line) {
            if (line.trim().isNotEmpty) {
              messages.add(line);
            }
            parent.print(zone, line);
          },
        ),
      );

      final issue = snapshot.issues.firstWhere(
        (candidate) => candidate.key == 'TRACK-12',
      );
      expect(
        issue.links.any(
          (link) =>
              link.type == 'blocks' &&
              link.direction == 'inward' &&
              link.targetKey == 'TRACK-11',
        ),
        isTrue,
      );

      final joinedMessages = messages.join('\n').toLowerCase();
      expect(joinedMessages, contains('warning'));
      expect(joinedMessages, contains('blocks'));
      expect(joinedMessages, contains('inward'));
      expect(joinedMessages, contains('outward'));
    },
  );
}

Future<Directory> _createRepository() async {
  final directory = await Directory.systemTemp.createTemp(
    'trackstate-link-warning-',
  );
  await _writeFile(
    directory,
    'TRACK/project.json',
    '{"key":"TRACK","name":"Link Warning Demo"}\n',
  );
  await _writeFile(
    directory,
    'TRACK/config/statuses.json',
    '${jsonEncode([
      {'id': 'todo', 'name': 'To Do'},
      {'id': 'in-progress', 'name': 'In Progress'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'TRACK/config/issue-types.json',
    '${jsonEncode([
      {'id': 'story', 'name': 'Story'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'TRACK/config/fields.json',
    '${jsonEncode([
      {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
      {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
    ])}\n',
  );
  await _writeFile(
    directory,
    'TRACK/config/priorities.json',
    '${jsonEncode([
      {'id': 'medium', 'name': 'Medium'},
      {'id': 'high', 'name': 'High'},
    ])}\n',
  );
  await _writeFile(
    directory,
    'TRACK/.trackstate/index/tombstones.json',
    '[]\n',
  );
  await _writeFile(directory, 'TRACK/TRACK-11/main.md', '''
---
key: TRACK-11
project: TRACK
issueType: story
status: todo
priority: medium
summary: Linked issue
assignee: demo-user
reporter: demo-admin
updated: 2026-05-05T00:00:00Z
---

# Summary

Linked issue

# Description

Receives the non-canonical link metadata.
''');
  await _writeFile(directory, 'TRACK/TRACK-12/main.md', '''
---
key: TRACK-12
project: TRACK
issueType: story
status: in-progress
priority: high
summary: Source issue
assignee: demo-user
reporter: demo-admin
updated: 2026-05-05T00:05:00Z
---

# Summary

Source issue

# Description

Stores the non-canonical link metadata fixture.
''');
  await _writeFile(
    directory,
    'TRACK/TRACK-12/links.json',
    '${jsonEncode([
      {'type': 'blocks', 'target': 'TRACK-11', 'direction': 'inward'},
    ])}\n',
  );

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
  await _git(directory.path, ['commit', '-m', 'Initial link warning fixture']);
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
