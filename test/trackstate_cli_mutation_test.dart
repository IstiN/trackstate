import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/cli/trackstate_cli.dart';

void main() {
  group('TrackStateCli mutations', () {
    test('creates tickets from jira_create_ticket_with_json', () async {
      final repo = await _createCliMutationRepository();
      addTearDown(() => repo.delete(recursive: true));
      final cli = _createCli();

      final result = await cli.run([
        'jira_create_ticket_with_json',
        '--target',
        'local',
        '--path',
        repo.path,
        '--json',
        jsonEncode({
          'fields': {
            'project': {'key': 'DEMO'},
            'summary': 'CLI created story',
            'description': 'Created from a Jira payload.',
            'issuetype': {'name': 'Story'},
            'priority': {'name': 'High'},
            'epic': {'key': 'DEMO-10'},
            'customfield_10016': 5,
          },
        }),
      ]);
      final json = jsonDecode(result.stdout) as Map<String, Object?>;
      final data = json['data']! as Map<String, Object?>;
      final issue = data['issue']! as Map<String, Object?>;

      expect(result.exitCode, 0);
      expect(json['ok'], isTrue);
      expect(data['command'], 'jira-create-ticket-with-json');
      expect(issue['key'], 'DEMO-11');
      expect(issue['epic'], 'DEMO-10');
      expect(issue['customFields'], containsPair('customfield_10016', 5));
      expect(
        data['revision'],
        isA<String>().having((value) => value, 'value', isNotEmpty),
      );
      expect(
        File('${repo.path}/DEMO/DEMO-10/DEMO-11/main.md').existsSync(),
        isTrue,
      );
    });

    test(
      'updates and clears fields by display name and customfield id',
      () async {
        final repo = await _createCliMutationRepository();
        addTearDown(() => repo.delete(recursive: true));
        final cli = _createCli();

        final updateResult = await cli.run([
          'ticket',
          'update-field',
          '--target',
          'local',
          '--path',
          repo.path,
          '--key',
          'DEMO-2',
          '--field',
          'Story Points',
          '--value',
          '13',
        ]);
        final updateJson =
            jsonDecode(updateResult.stdout) as Map<String, Object?>;
        final updateData = updateJson['data']! as Map<String, Object?>;
        final updatedIssue = updateData['issue']! as Map<String, Object?>;

        expect(updateResult.exitCode, 0);
        expect(updatedIssue['customFields'], <String, Object?>{
          'customfield_10016': 13,
        });

        final clearResult = await cli.run([
          'jira_clear_field',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issueKey',
          'DEMO-2',
          '--field',
          'customfield_10016',
        ]);
        final clearJson =
            jsonDecode(clearResult.stdout) as Map<String, Object?>;
        final clearData = clearJson['data']! as Map<String, Object?>;
        final clearedIssue = clearData['issue']! as Map<String, Object?>;

        expect(clearResult.exitCode, 0);
        expect(clearedIssue['customFields'], <String, Object?>{});
        expect(
          File('${repo.path}/DEMO/DEMO-1/DEMO-2/main.md').readAsStringSync(),
          isNot(contains('customfield_10016')),
        );
      },
    );

    test(
      'supports lifecycle mutations for status, assignee, labels, description, and hierarchy',
      () async {
        final repo = await _createCliMutationRepository();
        addTearDown(() => repo.delete(recursive: true));
        final cli = _createCli();

        final moveResult = await cli.run([
          'ticket',
          'move-status',
          '--target',
          'local',
          '--path',
          repo.path,
          '--key',
          'DEMO-2',
          '--status',
          'Done',
        ]);
        final moveJson = jsonDecode(moveResult.stdout) as Map<String, Object?>;
        final moveIssue =
            (moveJson['data']! as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(moveResult.exitCode, 0);
        expect(moveIssue['status'], 'done');
        expect(moveIssue['resolution'], 'done');

        final assignResult = await cli.run([
          'jira_assign_ticket_to',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issueKey',
          'DEMO-2',
          '--assignee',
          'cli-user',
        ]);
        final assignIssue =
            ((jsonDecode(assignResult.stdout) as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(assignResult.exitCode, 0);
        expect(assignIssue['assignee'], 'cli-user');

        final addLabelResult = await cli.run([
          'jira_add_label',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issueKey',
          'DEMO-2',
          '--label',
          'automation',
        ]);
        final addLabelIssue =
            ((jsonDecode(addLabelResult.stdout) as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(addLabelResult.exitCode, 0);
        expect(addLabelIssue['labels'], contains('automation'));

        final removeLabelResult = await cli.run([
          'ticket',
          'remove-label',
          '--target',
          'local',
          '--path',
          repo.path,
          '--key',
          'DEMO-2',
          '--label',
          'automation',
        ]);
        final removeLabelIssue =
            ((jsonDecode(removeLabelResult.stdout)
                        as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(removeLabelResult.exitCode, 0);
        expect(removeLabelIssue['labels'], isNot(contains('automation')));

        final descriptionResult = await cli.run([
          'jira_update_description',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issueKey',
          'DEMO-2',
          '--description',
          'Updated from the CLI mutation suite.',
        ]);
        final descriptionIssue =
            ((jsonDecode(descriptionResult.stdout)
                        as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(descriptionResult.exitCode, 0);
        expect(
          descriptionIssue['description'],
          'Updated from the CLI mutation suite.',
        );

        final parentResult = await cli.run([
          'jira_update_ticket_parent',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issueKey',
          'DEMO-2',
          '--parent',
          'DEMO-10',
        ]);
        final parentIssue =
            ((jsonDecode(parentResult.stdout) as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(parentResult.exitCode, 0);
        expect(parentIssue['epic'], 'DEMO-10');
        expect(
          File('${repo.path}/DEMO/DEMO-10/DEMO-2/main.md').existsSync(),
          isTrue,
        );
        expect(
          File('${repo.path}/DEMO/DEMO-1/DEMO-2/main.md').existsSync(),
          isFalse,
        );
      },
    );

    test('posts comments and links with canonical mutation payloads', () async {
      final repo = await _createCliMutationRepository();
      addTearDown(() => repo.delete(recursive: true));
      final cli = _createCli();

      final commentResult = await cli.run([
        'jira_post_comment',
        '--target',
        'local',
        '--path',
        repo.path,
        '--issueKey',
        'DEMO-2',
        '--body',
        'Automation comment.',
      ]);
      final commentData =
          (jsonDecode(commentResult.stdout) as Map<String, Object?>)['data']!
              as Map<String, Object?>;
      final comment = commentData['comment']! as Map<String, Object?>;
      expect(commentResult.exitCode, 0);
      expect(comment['id'], '0001');
      expect(comment['body'], 'Automation comment.');
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/comments/0001.md').existsSync(),
        isTrue,
      );

      final linkResult = await cli.run([
        'ticket',
        'link',
        '--target',
        'local',
        '--path',
        repo.path,
        '--key',
        'DEMO-2',
        '--target-key',
        'DEMO-10',
        '--type',
        'is blocked by',
      ]);
      final linkData =
          (jsonDecode(linkResult.stdout) as Map<String, Object?>)['data']!
              as Map<String, Object?>;
      final link = linkData['link']! as Map<String, Object?>;
      expect(linkResult.exitCode, 0);
      expect(link['type'], 'blocks');
      expect(link['direction'], 'inward');
      expect(
        File('${repo.path}/DEMO/DEMO-1/DEMO-2/links.json').readAsStringSync(),
        contains('"type":"blocks"'),
      );
    });

    test(
      'updates from jira JSON, archives explicitly, and deletes permanently',
      () async {
        final repo = await _createCliMutationRepository();
        addTearDown(() => repo.delete(recursive: true));
        final cli = _createCli();

        final updateResult = await cli.run([
          'jira_update_ticket',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issueKey',
          'DEMO-2',
          '--json',
          jsonEncode({
            'fields': {
              'summary': 'Updated from JSON',
              'description': 'JSON mutation body.',
              'priority': {'name': 'High'},
              'customfield_10016': 3,
            },
          }),
        ]);
        final updateIssue =
            ((jsonDecode(updateResult.stdout) as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(updateResult.exitCode, 0);
        expect(updateIssue['summary'], 'Updated from JSON');
        expect(updateIssue['priority'], 'high');
        expect(updateIssue['customFields'], <String, Object?>{
          'customfield_10016': 3,
        });

        final archiveResult = await cli.run([
          'ticket',
          'archive',
          '--target',
          'local',
          '--path',
          repo.path,
          '--key',
          'DEMO-10',
        ]);
        final archiveIssue =
            ((jsonDecode(archiveResult.stdout) as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        expect(archiveResult.exitCode, 0);
        expect(archiveIssue['archived'], isTrue);
        expect(
          File(
            '${repo.path}/DEMO/.trackstate/archive/DEMO-10/main.md',
          ).existsSync(),
          isTrue,
        );

        final createdDeleteTarget = await cli.run([
          'ticket',
          'create',
          '--target',
          'local',
          '--path',
          repo.path,
          '--summary',
          'Delete me',
          '--issue-type',
          'Story',
        ]);
        final createdIssue =
            ((jsonDecode(createdDeleteTarget.stdout)
                        as Map<String, Object?>)['data']
                    as Map<String, Object?>)['issue']!
                as Map<String, Object?>;
        final createdKey = createdIssue['key']! as String;

        final deleteResult = await cli.run([
          'jira_delete_ticket',
          '--target',
          'local',
          '--path',
          repo.path,
          '--issueKey',
          createdKey,
        ]);
        final deletedIssue =
            ((jsonDecode(deleteResult.stdout) as Map<String, Object?>)['data']
                    as Map<String, Object?>)['deletedIssue']!
                as Map<String, Object?>;
        expect(deleteResult.exitCode, 0);
        expect(deletedIssue['key'], createdKey);
        expect(
          File('${repo.path}/DEMO/$createdKey/main.md').existsSync(),
          isFalse,
        );
        expect(
          File(
            '${repo.path}/DEMO/.trackstate/tombstones/$createdKey.json',
          ).existsSync(),
          isTrue,
        );
      },
    );
  });
}

TrackStateCli _createCli() => TrackStateCli(
  environment: const TrackStateCliEnvironment(
    resolvePath: _identityPath,
    workingDirectory: '.',
  ),
);

String _identityPath(String path) => path;

Future<Directory> _createCliMutationRepository() async {
  final directory = await Directory.systemTemp.createTemp(
    'trackstate-cli-mutation-',
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
  await _git(directory.path, ['commit', '-m', 'Initial CLI mutation fixture']);
  return directory;
}

Map<String, String> _mutationFixtureFiles() {
  final files = <String, String>{
    'DEMO/project.json': '{"key":"DEMO","name":"CLI Mutation Demo"}\n',
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
          {'id': 'customfield_10016', 'name': 'Story Points', 'type': 'number', 'required': false},
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

Root epic for CLI mutation tests.
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
labels: ["existing"]
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Summary

Nested story

# Description

Story ready for CLI mutation tests.
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
  };
  files['DEMO/.trackstate/index/issues.json'] =
      '${jsonEncode(_mutationIndexEntries(files))}\n';
  return files;
}

List<Map<String, Object?>> _mutationIndexEntries(Map<String, String> files) => [
  {
    'key': 'DEMO-1',
    'path': 'DEMO/DEMO-1/main.md',
    'parent': null,
    'epic': null,
    'summary': 'Platform epic',
    'issueType': 'epic',
    'status': 'in-progress',
    'priority': 'high',
    'assignee': 'demo-admin',
    'labels': [],
    'updated': '2026-05-05T00:00:00Z',
    'revision': _blobRevisionForText(files['DEMO/DEMO-1/main.md']!),
    'children': ['DEMO-2'],
    'archived': false,
  },
  {
    'key': 'DEMO-2',
    'path': 'DEMO/DEMO-1/DEMO-2/main.md',
    'parent': null,
    'epic': 'DEMO-1',
    'summary': 'Nested story',
    'issueType': 'story',
    'status': 'in-review',
    'priority': 'medium',
    'assignee': 'demo-user',
    'labels': ['existing'],
    'updated': '2026-05-05T00:05:00Z',
    'revision': _blobRevisionForText(files['DEMO/DEMO-1/DEMO-2/main.md']!),
    'children': ['DEMO-3'],
    'archived': false,
  },
  {
    'key': 'DEMO-3',
    'path': 'DEMO/DEMO-1/DEMO-2/DEMO-3/main.md',
    'parent': 'DEMO-2',
    'epic': 'DEMO-1',
    'summary': 'Nested sub-task',
    'issueType': 'subtask',
    'status': 'todo',
    'priority': 'medium',
    'assignee': 'demo-user',
    'labels': [],
    'updated': '2026-05-05T00:10:00Z',
    'revision': _blobRevisionForText(
      files['DEMO/DEMO-1/DEMO-2/DEMO-3/main.md']!,
    ),
    'children': [],
    'archived': false,
  },
  {
    'key': 'DEMO-10',
    'path': 'DEMO/DEMO-10/main.md',
    'parent': null,
    'epic': null,
    'summary': 'Alternative epic',
    'issueType': 'epic',
    'status': 'todo',
    'priority': 'medium',
    'assignee': 'demo-admin',
    'labels': [],
    'updated': '2026-05-05T00:15:00Z',
    'revision': _blobRevisionForText(files['DEMO/DEMO-10/main.md']!),
    'children': [],
    'archived': false,
  },
];

String _blobRevisionForText(String content) {
  final bytes = Uint8List.fromList(utf8.encode(content));
  var value = 2166136261;
  for (final byte in bytes) {
    value ^= byte;
    value = (value * 16777619) & 0xffffffff;
  }
  final chunk = value.toRadixString(16).padLeft(8, '0');
  return List.filled(5, chunk).join().substring(0, 40);
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
