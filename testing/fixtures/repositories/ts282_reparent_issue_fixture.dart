import 'dart:convert';
import 'dart:io';

class Ts282ReparentIssueFixture {
  Ts282ReparentIssueFixture._(this.directory);

  static const projectKey = 'REPARENT';
  static const sourceParentKey = 'EPIC-1';
  static const targetParentKey = 'EPIC-2';
  static const movedIssueKey = 'TASK-1';
  static const movedIssueSummary = 'Keep task stable while moving folders';
  static const movedIssueDescription =
      'Task stays discoverable after the hierarchy move.';
  static const acceptanceCriterion =
      'Re-parenting preserves the issue key while the directory moves.';
  static const sourceParentSummary = 'Original epic parent';
  static const targetParentSummary = 'Destination epic parent';
  static const oldIssuePath =
      '$projectKey/$sourceParentKey/$movedIssueKey/main.md';
  static const newIssuePath =
      '$projectKey/$targetParentKey/$movedIssueKey/main.md';
  static const oldAcceptanceCriteriaPath =
      '$projectKey/$sourceParentKey/$movedIssueKey/acceptance_criteria.md';
  static const newAcceptanceCriteriaPath =
      '$projectKey/$targetParentKey/$movedIssueKey/acceptance_criteria.md';
  static const sourceParentPath = '$projectKey/$sourceParentKey/main.md';
  static const targetParentPath = '$projectKey/$targetParentKey/main.md';

  final Directory directory;

  String get repositoryPath => directory.path;

  static Future<Ts282ReparentIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-282-',
    );
    final fixture = Ts282ReparentIssueFixture._(directory);
    await fixture._seedRepository();
    return fixture;
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<Ts282RepositoryObservation> observeRepositoryState() async {
    final issueIndex = await _readIssueIndex();
    final movedIssueEntry = _indexEntryForKey(issueIndex, movedIssueKey);
    final sourceParentEntry = _indexEntryForKey(issueIndex, sourceParentKey);
    final targetParentEntry = _indexEntryForKey(issueIndex, targetParentKey);
    final newIssueFile = File('${directory.path}/$newIssuePath');
    final newIssueContent = await _readIfExists(newIssueFile);
    final newFrontmatter = newIssueContent == null
        ? const <String, String>{}
        : _parseFrontmatter(newIssueContent);

    return Ts282RepositoryObservation(
      oldIssueDirectoryExists: Directory(
        '${directory.path}/${_issueRoot(oldIssuePath)}',
      ).existsSync(),
      newIssueDirectoryExists: Directory(
        '${directory.path}/${_issueRoot(newIssuePath)}',
      ).existsSync(),
      oldIssueFileExists: File('${directory.path}/$oldIssuePath').existsSync(),
      newIssueFileExists: newIssueFile.existsSync(),
      oldAcceptanceCriteriaExists: File(
        '${directory.path}/$oldAcceptanceCriteriaPath',
      ).existsSync(),
      newAcceptanceCriteriaExists: File(
        '${directory.path}/$newAcceptanceCriteriaPath',
      ).existsSync(),
      newIssueMarkdown: newIssueContent,
      newIssueFrontmatter: newFrontmatter,
      issueIndexPath: movedIssueEntry?['path']?.toString(),
      issueIndexParentKey: _nullable(movedIssueEntry?['parent']?.toString()),
      issueIndexEpicKey: _nullable(movedIssueEntry?['epic']?.toString()),
      issueIndexParentPath: _nullable(
        movedIssueEntry?['parentPath']?.toString(),
      ),
      issueIndexEpicPath: _nullable(movedIssueEntry?['epicPath']?.toString()),
      sourceParentChildKeys: _stringList(sourceParentEntry?['children']),
      targetParentChildKeys: _stringList(targetParentEntry?['children']),
      worktreeStatusLines: await _gitLines(['status', '--short']),
      headRevision: await _gitSingleLine(['rev-parse', 'HEAD']),
      latestCommitSubject: await _gitSingleLine(['log', '-1', '--pretty=%s']),
      renameStatusLines: await _gitLines([
        'diff-tree',
        '--no-commit-id',
        '--name-status',
        '-r',
        '-M',
        'HEAD',
      ]),
    );
  }

  Future<void> _seedRepository() async {
    for (final entry in _fixtureFiles().entries) {
      await _writeFile(entry.key, entry.value);
    }
    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed TS-282 reparent fixture']);
  }

  Map<String, String> _fixtureFiles() => {
    '$projectKey/project.json': jsonEncode({
      'key': projectKey,
      'name': 'Issue reparent demo',
    }),
    '$projectKey/config/statuses.json':
        '${jsonEncode([
          {'id': 'todo', 'name': 'To Do'},
          {'id': 'in-progress', 'name': 'In Progress'},
          {'id': 'done', 'name': 'Done'},
        ])}\n',
    '$projectKey/config/issue-types.json':
        '${jsonEncode([
          {'id': 'epic', 'name': 'Epic'},
          {'id': 'story', 'name': 'Story'},
        ])}\n',
    '$projectKey/config/fields.json':
        '${jsonEncode([
          {'id': 'summary', 'name': 'Summary', 'type': 'string', 'required': true},
          {'id': 'description', 'name': 'Description', 'type': 'markdown', 'required': false},
        ])}\n',
    '$projectKey/config/priorities.json':
        '${jsonEncode([
          {'id': 'medium', 'name': 'Medium'},
          {'id': 'high', 'name': 'High'},
        ])}\n',
    '$projectKey/config/resolutions.json': '[]\n',
    '$projectKey/config/workflows.json':
        '${jsonEncode({
          'default': {
            'statuses': ['To Do', 'In Progress', 'Done'],
            'transitions': [
              {'id': 'start', 'name': 'Start work', 'from': 'To Do', 'to': 'In Progress'},
              {'id': 'complete', 'name': 'Complete', 'from': 'In Progress', 'to': 'Done'},
            ],
          },
        })}\n',
    '$projectKey/.trackstate/index/issues.json':
        '${jsonEncode([
          {
            'key': sourceParentKey,
            'path': sourceParentPath,
            'parent': null,
            'epic': null,
            'children': [movedIssueKey],
            'archived': false,
          },
          {'key': targetParentKey, 'path': targetParentPath, 'parent': null, 'epic': null, 'children': <String>[], 'archived': false},
          {'key': movedIssueKey, 'path': oldIssuePath, 'parent': null, 'epic': sourceParentKey, 'children': <String>[], 'archived': false},
        ])}\n',
    '$projectKey/.trackstate/index/tombstones.json': '[]\n',
    sourceParentPath:
        '''
---
key: $sourceParentKey
project: $projectKey
issueType: epic
status: in-progress
priority: high
summary: $sourceParentSummary
assignee: qa-owner
reporter: qa-owner
updated: 2026-05-10T00:00:00Z
---

# Summary

$sourceParentSummary

# Description

Original parent epic for the re-parent scenario.
''',
    targetParentPath:
        '''
---
key: $targetParentKey
project: $projectKey
issueType: epic
status: todo
priority: high
summary: $targetParentSummary
assignee: qa-owner
reporter: qa-owner
updated: 2026-05-10T00:01:00Z
---

# Summary

$targetParentSummary

# Description

Destination epic for the re-parent scenario.
''',
    oldIssuePath:
        '''
---
key: $movedIssueKey
project: $projectKey
issueType: story
status: in-progress
priority: medium
summary: $movedIssueSummary
assignee: qa-owner
reporter: qa-owner
epic: $sourceParentKey
updated: 2026-05-10T00:02:00Z
---

# Summary

$movedIssueSummary

# Description

$movedIssueDescription
''',
    oldAcceptanceCriteriaPath: '- $acceptanceCriterion\n',
    '.gitattributes': '*.png filter=lfs diff=lfs merge=lfs -text\n',
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

  Future<String?> _readIfExists(File file) async {
    if (!file.existsSync()) {
      return null;
    }
    return file.readAsString();
  }

  Future<List<Map<String, Object?>>> _readIssueIndex() async {
    final decoded = jsonDecode(
      await File(
        '${directory.path}/$projectKey/.trackstate/index/issues.json',
      ).readAsString(),
    );
    if (decoded is! List) {
      throw StateError('TS-282 expected issues.json to decode as a list.');
    }
    return decoded
        .whereType<Map>()
        .map((entry) => Map<String, Object?>.from(entry))
        .toList(growable: false);
  }

  Map<String, Object?>? _indexEntryForKey(
    List<Map<String, Object?>> issueIndex,
    String key,
  ) {
    for (final entry in issueIndex) {
      if (entry['key'] == key) {
        return entry;
      }
    }
    return null;
  }

  Map<String, String> _parseFrontmatter(String content) {
    final lines = content.split('\n');
    if (lines.isEmpty || lines.first.trim() != '---') {
      return const {};
    }
    final metadata = <String, String>{};
    for (var index = 1; index < lines.length; index++) {
      final line = lines[index].trimRight();
      if (line.trim() == '---') {
        break;
      }
      final match = RegExp(
        r'^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$',
      ).firstMatch(line);
      if (match == null) {
        continue;
      }
      metadata[match.group(1)!] = match.group(2)!.trim();
    }
    return metadata;
  }

  List<String> _stringList(Object? value) {
    if (value is! List) {
      return const [];
    }
    return value
        .map((entry) => entry.toString())
        .where((entry) => entry.isNotEmpty)
        .toList(growable: false);
  }

  Future<List<String>> _gitLines(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
    final output = result.stdout.toString().trim();
    if (output.isEmpty) {
      return const [];
    }
    return output
        .split('\n')
        .map((line) => line.trimRight())
        .where((line) => line.isNotEmpty)
        .toList(growable: false);
  }

  Future<String> _gitSingleLine(List<String> args) async {
    final lines = await _gitLines(args);
    if (lines.isEmpty) {
      throw StateError('git ${args.join(' ')} returned no output.');
    }
    return lines.first;
  }

  String _issueRoot(String issuePath) =>
      issuePath.substring(0, issuePath.lastIndexOf('/'));

  String? _nullable(String? value) {
    if (value == null || value.isEmpty || value == 'null') {
      return null;
    }
    return value;
  }
}

class Ts282RepositoryObservation {
  const Ts282RepositoryObservation({
    required this.oldIssueDirectoryExists,
    required this.newIssueDirectoryExists,
    required this.oldIssueFileExists,
    required this.newIssueFileExists,
    required this.oldAcceptanceCriteriaExists,
    required this.newAcceptanceCriteriaExists,
    required this.newIssueMarkdown,
    required this.newIssueFrontmatter,
    required this.issueIndexPath,
    required this.issueIndexParentKey,
    required this.issueIndexEpicKey,
    required this.issueIndexParentPath,
    required this.issueIndexEpicPath,
    required this.sourceParentChildKeys,
    required this.targetParentChildKeys,
    required this.worktreeStatusLines,
    required this.headRevision,
    required this.latestCommitSubject,
    required this.renameStatusLines,
  });

  final bool oldIssueDirectoryExists;
  final bool newIssueDirectoryExists;
  final bool oldIssueFileExists;
  final bool newIssueFileExists;
  final bool oldAcceptanceCriteriaExists;
  final bool newAcceptanceCriteriaExists;
  final String? newIssueMarkdown;
  final Map<String, String> newIssueFrontmatter;
  final String? issueIndexPath;
  final String? issueIndexParentKey;
  final String? issueIndexEpicKey;
  final String? issueIndexParentPath;
  final String? issueIndexEpicPath;
  final List<String> sourceParentChildKeys;
  final List<String> targetParentChildKeys;
  final List<String> worktreeStatusLines;
  final String headRevision;
  final String latestCommitSubject;
  final List<String> renameStatusLines;
}
