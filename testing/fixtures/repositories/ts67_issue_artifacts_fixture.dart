import 'dart:convert';
import 'dart:io';

class Ts67IssueArtifactsFixture {
  Ts67IssueArtifactsFixture._(this._directory);

  final Directory _directory;

  static const issueKey = 'DEMO-2';
  static const issueSummary = 'Hydrate side-car artifacts';
  String get path => _directory.path;

  List<Ts67ExpectedComment> get expectedComments => const [
    Ts67ExpectedComment(
      id: '0001',
      author: 'qa-bot',
      body: 'First markdown comment loaded from the repository side-car.',
      storagePath: 'DEMO/DEMO-1/DEMO-2/comments/0001.md',
    ),
    Ts67ExpectedComment(
      id: '0002',
      author: 'product-owner',
      body: 'Second markdown comment stays attached to the same issue.',
      storagePath: 'DEMO/DEMO-1/DEMO-2/comments/0002.md',
    ),
  ];

  List<Ts67ExpectedLink> get expectedLinks => const [
    Ts67ExpectedLink(type: 'blocks', targetKey: 'DEMO-9', direction: 'outward'),
    Ts67ExpectedLink(
      type: 'relates-to',
      targetKey: 'DEMO-10',
      direction: 'inward',
    ),
  ];

  static Future<Ts67IssueArtifactsFixture> create() async {
    final directory = Directory.systemTemp.createTempSync('trackstate-ts-67-');
    final fixture = Ts67IssueArtifactsFixture._(directory);
    fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() async {
    _directory.deleteSync(recursive: true);
  }

  void _seedRepository() {
    _writeFile('.gitattributes', '*.png filter=lfs diff=lfs merge=lfs -text\n');
    _writeFile(
      'DEMO/project.json',
      '{"key":"DEMO","name":"Issue Artifact Demo"}\n',
    );
    _writeFile(
      'DEMO/config/statuses.json',
      '[{"name":"To Do"},{"name":"In Progress"},{"name":"Done"}]\n',
    );
    _writeFile(
      'DEMO/config/issue-types.json',
      '[{"name":"Epic"},{"name":"Story"},{"name":"Task"}]\n',
    );
    _writeFile(
      'DEMO/config/fields.json',
      '[{"name":"Summary"},{"name":"Priority"}]\n',
    );
    _writeFile('DEMO/DEMO-1/main.md', '''
---
key: DEMO-1
project: DEMO
issueType: Epic
status: To Do
priority: High
summary: Artifact hydration epic
assignee: demo-lead
reporter: demo-lead
updated: 2026-05-06T09:00:00Z
---

# Description

Parent issue for artifact hydration coverage.
''');
    _writeFile('DEMO/DEMO-1/DEMO-2/main.md', '''
---
key: DEMO-2
project: DEMO
issueType: Story
status: To Do
priority: High
summary: Hydrate side-car artifacts
assignee: qa-bot
reporter: product-owner
updated: 2026-05-06T09:15:00Z
---

# Description

Issue detail should load comments and links from side-car files.
''');
    _writeFile('DEMO/DEMO-1/DEMO-2/comments/0001.md', '''
---
author: qa-bot
created: 2026-05-06T10:00:00Z
---

First markdown comment loaded from the repository side-car.
''');
    _writeFile('DEMO/DEMO-1/DEMO-2/comments/0002.md', '''
---
author: product-owner
created: 2026-05-06T11:30:00Z
---

Second markdown comment stays attached to the same issue.
''');
    _writeFile(
      'DEMO/DEMO-1/DEMO-2/links.json',
      jsonEncode([
        {'type': 'blocks', 'target': 'DEMO-9', 'direction': 'outward'},
        {'type': 'relates-to', 'targetKey': 'DEMO-10', 'direction': 'inward'},
      ]),
    );
    _writeFile('DEMO/DEMO-9/main.md', '''
---
key: DEMO-9
project: DEMO
issueType: Task
status: In Progress
priority: Medium
summary: Blocked task
assignee: api-user
reporter: api-user
updated: 2026-05-06T09:30:00Z
---

# Description

Linked task used to verify non-hierarchical relationships.
''');
    _writeFile('DEMO/DEMO-10/main.md', '''
---
key: DEMO-10
project: DEMO
issueType: Task
status: To Do
priority: Low
summary: Related task
assignee: api-user
reporter: api-user
updated: 2026-05-06T09:45:00Z
---

# Description

Another linked task used to verify alternate link keys.
''');

    _git(['init', '-b', 'main']);
    _git(['config', '--local', 'user.name', 'TS-67 Tester']);
    _git(['config', '--local', 'user.email', 'ts67@example.com']);
    _git(['add', '.']);
    _git(['commit', '-m', 'Seed TS-67 issue artifacts fixture']);
  }

  void _writeFile(String relativePath, String content) {
    final file = File('${_directory.path}/$relativePath');
    file.parent.createSync(recursive: true);
    file.writeAsStringSync(content);
  }

  void _git(List<String> args) {
    final result = Process.runSync('git', ['-C', _directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}

class Ts67ExpectedComment {
  const Ts67ExpectedComment({
    required this.id,
    required this.author,
    required this.body,
    required this.storagePath,
  });

  final String id;
  final String author;
  final String body;
  final String storagePath;
}

class Ts67ExpectedLink {
  const Ts67ExpectedLink({
    required this.type,
    required this.targetKey,
    required this.direction,
  });

  final String type;
  final String targetKey;
  final String direction;
}
