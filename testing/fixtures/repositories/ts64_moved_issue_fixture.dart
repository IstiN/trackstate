import 'dart:convert';
import 'dart:io';

import 'package:trackstate/data/repositories/local_trackstate_repository.dart';

import '../../components/services/issue_key_resolution_service.dart';

class Ts64MovedIssueFixture {
  Ts64MovedIssueFixture._({
    required this.directory,
    required this.repository,
    required this.service,
  });

  static const projectKey = 'PROJECT';
  static const movedIssueKey = 'PROJECT-1';
  static const movedIssueSummary = 'Moved issue stays discoverable';
  static const movedIssuePath = 'PROJECT/NEW-PARENT/PROJECT-1/main.md';
  static const movedIssueCriterion = 'Lookup stays stable after path move.';
  static const parentIssueKey = 'PROJECT-9';
  static const parentIssuePath = 'PROJECT/NEW-PARENT/main.md';
  static const legacyIssuePath = 'PROJECT/PROJECT-1/main.md';
  static const siblingIssueKey = 'PROJECT-2';
  static const siblingIssueSummary =
      'Sibling issue remains visible before filtering';

  final Directory directory;
  final LocalTrackStateRepository repository;
  final IssueKeyResolutionService service;

  String get repositoryPath => directory.path;

  static Future<Ts64MovedIssueFixture> create() async {
    final directory = await Directory.systemTemp.createTemp(
      'trackstate-ts-64-',
    );
    final repository = LocalTrackStateRepository(
      repositoryPath: directory.path,
    );
    final fixture = Ts64MovedIssueFixture._(
      directory: directory,
      repository: repository,
      service: IssueKeyResolutionService(repository: repository),
    );
    await fixture._seedRepository();
    return fixture;
  }

  Future<bool> legacyIssueExists() async =>
      File('${directory.path}/$legacyIssuePath').exists();

  Future<Ts64IndexArtifactsObservation> observeRebuiltIndexes() async {
    final issueIndex = await _readIssueIndex();
    final hierarchyIndex = await _readHierarchyIndex();
    final movedIssueEntry = _indexEntryForKey(issueIndex, movedIssueKey);
    final parentIssueEntry = _indexEntryForKey(issueIndex, parentIssueKey);
    final movedHierarchyNode = _hierarchyNodeForKey(
      hierarchyIndex,
      movedIssueKey,
    );
    final parentHierarchyNode = _hierarchyNodeForKey(
      hierarchyIndex,
      parentIssueKey,
    );

    return Ts64IndexArtifactsObservation(
      issueIndexPath: movedIssueEntry?['path']?.toString(),
      issueIndexParentPath: movedIssueEntry?['parentPath']?.toString(),
      issueIndexParentChildKeys: _stringList(parentIssueEntry?['children']),
      hierarchyPath: movedHierarchyNode?['path']?.toString(),
      hierarchyParentChildKeys: _stringList(parentHierarchyNode?['children']),
      legacyPathReferenced:
          _jsonContainsLegacyPath(issueIndex) ||
          _jsonContainsLegacyPath(hierarchyIndex),
    );
  }

  Future<void> dispose() => directory.delete(recursive: true);

  Future<void> _seedRepository() async {
    await _git(['init', '-b', 'main']);
    await _git(['config', '--local', 'user.name', 'Local Tester']);
    await _git(['config', '--local', 'user.email', 'local@example.com']);

    await _writeProjectConfig();
    await _writeLegacyRepositoryState();
    await _rebuildIndexes();
    await _git(['add', '.']);
    await _git(['commit', '-m', 'Seed TS-64 legacy issue fixture']);

    await _moveIssueDirectory();
    await _rebuildIndexes();
    await _git(['add', '-A']);
    await _git(['commit', '-m', 'Move PROJECT-1 and rebuild indexes']);
  }

  Future<void> _writeFile(String relativePath, String content) async {
    final file = File('${directory.path}/$relativePath');
    await file.parent.create(recursive: true);
    await file.writeAsString(content);
  }

  Future<void> _writeProjectConfig() async {
    await _writeFile(
      'PROJECT/project.json',
      jsonEncode({'key': projectKey, 'name': 'Moved issue demo'}),
    );
    await _writeFile(
      'PROJECT/config/statuses.json',
      jsonEncode([
        {'id': 'todo', 'name': 'To Do'},
        {'id': 'in-progress', 'name': 'In Progress'},
        {'id': 'done', 'name': 'Done'},
      ]),
    );
    await _writeFile(
      'PROJECT/config/issue-types.json',
      jsonEncode([
        {'id': 'story', 'name': 'Story'},
      ]),
    );
    await _writeFile(
      'PROJECT/config/fields.json',
      jsonEncode([
        {'id': 'summary', 'name': 'Summary'},
        {'id': 'priority', 'name': 'Priority'},
      ]),
    );
  }

  Future<void> _writeLegacyRepositoryState() async {
    await _writeFile(parentIssuePath, '''
---
key: $parentIssueKey
project: $projectKey
issueType: story
status: done
priority: high
summary: New parent after move
assignee: qa-owner
reporter: qa-owner
updated: 2026-05-07T00:00:00Z
---

# Description

Parent issue anchoring the moved child directory.
''');
    await _writeIssue(
      path: legacyIssuePath,
      key: movedIssueKey,
      summary: movedIssueSummary,
      description: 'Loads from the regenerated repository index.',
      acceptanceCriterion: movedIssueCriterion,
      parentKey: parentIssueKey,
    );
    await _writeIssue(
      path: 'PROJECT/OTHER-AREA/PROJECT-2/main.md',
      key: siblingIssueKey,
      summary: siblingIssueSummary,
      description:
          'Control issue that should disappear after filtering by key.',
      acceptanceCriterion: 'Filtering by key should hide unrelated issues.',
    );
  }

  Future<void> _writeIssue({
    required String path,
    required String key,
    required String summary,
    required String description,
    required String acceptanceCriterion,
    String? parentKey,
  }) async {
    await _writeFile(path, '''
---
key: $key
project: $projectKey
issueType: story
status: in-progress
priority: high
summary: $summary
assignee: qa-owner
reporter: qa-owner
parent: ${parentKey ?? 'null'}
updated: 2026-05-07T00:05:00Z
---

# Description

$description
''');
    final issueRoot = path.substring(0, path.lastIndexOf('/'));
    await _writeFile(
      '$issueRoot/acceptance_criteria.md',
      '- $acceptanceCriterion\n',
    );
  }

  Future<void> _moveIssueDirectory() async {
    final legacyDirectory = Directory('${directory.path}/PROJECT/PROJECT-1');
    final movedDirectory = Directory(
      '${directory.path}/PROJECT/NEW-PARENT/PROJECT-1',
    );
    await movedDirectory.parent.create(recursive: true);
    await legacyDirectory.rename(movedDirectory.path);
  }

  Future<void> _rebuildIndexes() async {
    final issues = await _discoverIssues();
    final entriesByKey = {for (final issue in issues) issue.key: issue};
    final pathByKey = {for (final issue in issues) issue.key: issue.path};
    final childrenByKey = <String, List<String>>{};
    for (final issue in issues) {
      final relationshipParent = issue.parentKey ?? issue.epicKey;
      if (relationshipParent == null) continue;
      childrenByKey
          .putIfAbsent(relationshipParent, () => <String>[])
          .add(issue.key);
    }

    final issueIndex = [
      for (final issue in issues)
        {
          'key': issue.key,
          'path': issue.path,
          'parent': issue.parentKey,
          'parentPath': issue.parentKey == null
              ? null
              : pathByKey[issue.parentKey!],
          'epic': issue.epicKey,
          'epicPath': issue.epicKey == null ? null : pathByKey[issue.epicKey!],
          'children': [...(childrenByKey[issue.key] ?? const <String>[])]
            ..sort(),
          'archived': issue.isArchived,
        },
    ];

    final rootIssues =
        issues
            .where((issue) => issue.parentKey == null && issue.epicKey == null)
            .toList()
          ..sort((left, right) => left.key.compareTo(right.key));

    final hierarchyIndex = {
      'roots': [
        for (final issue in rootIssues)
          _buildHierarchyNode(
            issue: issue,
            entriesByKey: entriesByKey,
            childrenByKey: childrenByKey,
          ),
      ],
    };

    await _writeFile(
      'PROJECT/.trackstate/index/issues.json',
      const JsonEncoder.withIndent('  ').convert(issueIndex),
    );
    await _writeFile(
      'PROJECT/.trackstate/index/hierarchy.json',
      const JsonEncoder.withIndent('  ').convert(hierarchyIndex),
    );
  }

  Future<List<_IndexedIssue>> _discoverIssues() async {
    final files = await directory
        .list(recursive: true, followLinks: false)
        .where((entity) => entity is File)
        .cast<File>()
        .where((file) {
          final path = _relativePath(file.path);
          return path.endsWith('/main.md') && !path.contains('/.trackstate/');
        })
        .toList();
    files.sort((left, right) => left.path.compareTo(right.path));
    final issues = <_IndexedIssue>[];
    for (final file in files) {
      issues.add(await _readIndexedIssue(file));
    }
    issues.sort((left, right) => left.key.compareTo(right.key));
    return issues;
  }

  Future<_IndexedIssue> _readIndexedIssue(File file) async {
    final metadata = _parseFrontmatter(await file.readAsString());
    return _IndexedIssue(
      key: metadata['key'] ?? '',
      path: _relativePath(file.path),
      parentKey: _nullable(metadata['parent']),
      epicKey: _nullable(metadata['epic']),
      isArchived: (metadata['archived'] ?? '').toLowerCase() == 'true',
    );
  }

  Map<String, Object?> _buildHierarchyNode({
    required _IndexedIssue issue,
    required Map<String, _IndexedIssue> entriesByKey,
    required Map<String, List<String>> childrenByKey,
  }) {
    final childKeys = [...(childrenByKey[issue.key] ?? const <String>[])]
      ..sort();
    return {
      'key': issue.key,
      'path': issue.path,
      'parent': issue.parentKey,
      'epic': issue.epicKey,
      'children': [
        for (final childKey in childKeys)
          if (entriesByKey[childKey] case final childIssue?)
            _buildHierarchyNode(
              issue: childIssue,
              entriesByKey: entriesByKey,
              childrenByKey: childrenByKey,
            ),
      ],
    };
  }

  Future<List<Map<String, Object?>>> _readIssueIndex() async {
    final decoded = jsonDecode(
      await File(
        '${directory.path}/PROJECT/.trackstate/index/issues.json',
      ).readAsString(),
    );
    if (decoded is! List) {
      throw StateError('TS-64 expected issues.json to decode as a list.');
    }
    return decoded
        .whereType<Map>()
        .map((entry) {
          return Map<String, Object?>.from(entry);
        })
        .toList(growable: false);
  }

  Future<Map<String, Object?>> _readHierarchyIndex() async {
    final decoded = jsonDecode(
      await File(
        '${directory.path}/PROJECT/.trackstate/index/hierarchy.json',
      ).readAsString(),
    );
    if (decoded is! Map) {
      throw StateError('TS-64 expected hierarchy.json to decode as an object.');
    }
    return Map<String, Object?>.from(decoded);
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

  Map<String, Object?>? _hierarchyNodeForKey(
    Map<String, Object?> hierarchy,
    String key,
  ) {
    final roots = hierarchy['roots'];
    if (roots is! List) {
      return null;
    }
    return _findHierarchyNode(roots, key);
  }

  Map<String, Object?>? _findHierarchyNode(List<dynamic> nodes, String key) {
    for (final node in nodes) {
      if (node is! Map) continue;
      final map = Map<String, Object?>.from(node);
      if (map['key'] == key) {
        return map;
      }
      final children = map['children'];
      if (children is List) {
        final match = _findHierarchyNode(children, key);
        if (match != null) {
          return match;
        }
      }
    }
    return null;
  }

  bool _jsonContainsLegacyPath(Object? value) {
    if (value is String) {
      return value == legacyIssuePath;
    }
    if (value is List) {
      return value.any(_jsonContainsLegacyPath);
    }
    if (value is Map) {
      return value.values.any(_jsonContainsLegacyPath);
    }
    return false;
  }

  List<String> _stringList(Object? value) {
    if (value is! List) {
      return const [];
    }
    return value
        .map((entry) {
          if (entry is Map) {
            return entry['key']?.toString() ?? '';
          }
          return entry.toString();
        })
        .where((entry) => entry.isNotEmpty)
        .toList(growable: false);
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

  String _relativePath(String absolutePath) {
    final normalizedRoot = directory.path.replaceAll('\\', '/');
    final normalizedPath = absolutePath.replaceAll('\\', '/');
    return normalizedPath.substring(normalizedRoot.length + 1);
  }

  String? _nullable(String? value) {
    if (value == null || value.isEmpty || value == 'null') {
      return null;
    }
    return value;
  }

  Future<void> _git(List<String> args) async {
    final result = await Process.run('git', ['-C', directory.path, ...args]);
    if (result.exitCode != 0) {
      throw StateError('git ${args.join(' ')} failed: ${result.stderr}');
    }
  }
}

class Ts64IndexArtifactsObservation {
  const Ts64IndexArtifactsObservation({
    required this.issueIndexPath,
    required this.issueIndexParentPath,
    required this.issueIndexParentChildKeys,
    required this.hierarchyPath,
    required this.hierarchyParentChildKeys,
    required this.legacyPathReferenced,
  });

  final String? issueIndexPath;
  final String? issueIndexParentPath;
  final List<String> issueIndexParentChildKeys;
  final String? hierarchyPath;
  final List<String> hierarchyParentChildKeys;
  final bool legacyPathReferenced;
}

class _IndexedIssue {
  const _IndexedIssue({
    required this.key,
    required this.path,
    required this.parentKey,
    required this.epicKey,
    required this.isArchived,
  });

  final String key;
  final String path;
  final String? parentKey;
  final String? epicKey;
  final bool isArchived;
}
