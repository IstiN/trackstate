import 'dart:convert';
import 'dart:io';

class Ts284InverseLinkNormalizationFixture {
  Ts284InverseLinkNormalizationFixture._(this.directory);

  final Directory directory;

  static const sourceIssueKey = 'DEMO-2';
  static const targetIssueKey = 'DEMO-10';
  static const inverseLabel = 'is blocked by';
  static const canonicalType = 'blocks';
  static const canonicalDirection = 'inward';
  static const sourceLinksPath = 'DEMO/DEMO-1/DEMO-2/links.json';

  String get repositoryPath => directory.path;

  static Future<Ts284InverseLinkNormalizationFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-284-',
    );
    final fixture = Ts284InverseLinkNormalizationFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts284PersistedLinkObservation> observePersistedLinkState() async {
    final sourceLinksFile = File('$repositoryPath/$sourceLinksPath');
    final sourceLinksExists = await sourceLinksFile.exists();
    final rawLinksFileContent = sourceLinksExists
        ? await sourceLinksFile.readAsString()
        : null;
    final persistedLinks = rawLinksFileContent == null
        ? const <Map<String, Object?>>[]
        : _decodeLinks(rawLinksFileContent);

    return Ts284PersistedLinkObservation(
      sourceLinksPath: sourceLinksPath,
      sourceLinksExists: sourceLinksExists,
      rawLinksFileContent: rawLinksFileContent,
      persistedLinks: List<Map<String, Object?>>.unmodifiable(persistedLinks),
      linksJsonFiles: List<String>.unmodifiable(await _collectLinksJsonFiles()),
    );
  }

  Future<List<String>> _collectLinksJsonFiles() async {
    final files = await directory
        .list(recursive: true)
        .where((entry) => entry is File && entry.path.endsWith('/links.json'))
        .map(
          (entry) => entry.path
              .substring(directory.path.length + 1)
              .replaceAll('\\', '/'),
        )
        .toList();
    files.sort();
    return files;
  }

  Future<void> _seedRepository() async {
    for (final entry in _fixtureFiles().entries) {
      await _writeFile(entry.key, entry.value);
    }

    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed inverse-link fixture for TS-284']);
  }

  Map<String, String> _fixtureFiles() => {
    'DEMO/project.json': '{"key":"DEMO","name":"Mutation Demo"}\n',
    'DEMO/config/statuses.json':
        '${jsonEncode([
          {'id': 'todo', 'name': 'To Do'},
          {'id': 'in-review', 'name': 'In Review'},
        ])}\n',
    'DEMO/config/issue-types.json':
        '${jsonEncode([
          {'id': 'epic', 'name': 'Epic'},
          {'id': 'story', 'name': 'Story'},
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
          {'key': sourceIssueKey, 'path': 'DEMO/DEMO-1/DEMO-2/main.md', 'parent': null, 'epic': 'DEMO-1', 'children': const [], 'archived': false},
          {'key': targetIssueKey, 'path': 'DEMO/DEMO-10/main.md', 'parent': null, 'epic': null, 'children': const [], 'archived': false},
        ])}\n',
    'DEMO/.trackstate/index/tombstones.json': '[]\n',
    'DEMO/DEMO-1/main.md': '''
---
key: DEMO-1
project: DEMO
issueType: epic
status: in-review
priority: high
summary: Platform epic
updated: 2026-05-05T00:00:00Z
---

# Summary

Platform epic

# Description

Root epic for TS-284.
''',
    'DEMO/DEMO-1/DEMO-2/main.md':
        '''
---
key: $sourceIssueKey
project: DEMO
issueType: story
status: in-review
priority: medium
summary: Source story
epic: DEMO-1
updated: 2026-05-05T00:05:00Z
---

# Summary

Source story

# Description

Issue used as the inverse-link mutation source for TS-284.
''',
    'DEMO/DEMO-10/main.md':
        '''
---
key: $targetIssueKey
project: DEMO
issueType: epic
status: todo
priority: medium
summary: Blocking epic
updated: 2026-05-05T00:15:00Z
---

# Summary

Blocking epic

# Description

Issue used as the normalized outward-link target for TS-284.
''',
  };

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}

class Ts284PersistedLinkObservation {
  const Ts284PersistedLinkObservation({
    required this.sourceLinksPath,
    required this.sourceLinksExists,
    required this.rawLinksFileContent,
    required this.persistedLinks,
    required this.linksJsonFiles,
  });

  final String sourceLinksPath;
  final bool sourceLinksExists;
  final String? rawLinksFileContent;
  final List<Map<String, Object?>> persistedLinks;
  final List<String> linksJsonFiles;
}

List<Map<String, Object?>> _decodeLinks(String content) {
  final decoded = jsonDecode(content);
  if (decoded is! List) {
    return const <Map<String, Object?>>[];
  }
  return decoded
      .whereType<Map>()
      .map((entry) => Map<String, Object?>.from(entry))
      .toList(growable: false);
}
