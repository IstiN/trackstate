import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'trackstate-setup demo exposes three discovery fixtures across fields',
    () async {
      final demoRoot = Directory('trackstate-setup/DEMO');
      expect(demoRoot.existsSync(), isTrue);

      final summaryMatches = <String>[];
      final descriptionMatches = <String>[];
      final acceptanceMatches = <String>[];

      for (final entity in demoRoot.listSync(recursive: true)) {
        if (entity is! File ||
            entity.path.split(Platform.pathSeparator).last != 'main.md') {
          continue;
        }
        final issueDir = entity.parent;
        final key = issueDir.path.split(Platform.pathSeparator).last;
        final mainMarkdown = await entity.readAsString();
        final acceptanceFile = File(
          '${issueDir.path}${Platform.pathSeparator}acceptance_criteria.md',
        );
        final acceptanceMarkdown = acceptanceFile.existsSync()
            ? await acceptanceFile.readAsString()
            : '';

        final summary = _frontMatterValue(
          mainMarkdown,
          'summary',
        ).toLowerCase();
        final description = _section(mainMarkdown, 'Description').toLowerCase();
        final acceptance = _bulletItems(
          acceptanceMarkdown,
        ).join('\n').toLowerCase();

        if (summary.contains('discovery')) {
          summaryMatches.add(key);
        }
        if (description.contains('discovery')) {
          descriptionMatches.add(key);
        }
        if (acceptance.contains('discovery')) {
          acceptanceMatches.add(key);
        }
      }

      final allMatches = {
        ...summaryMatches,
        ...descriptionMatches,
        ...acceptanceMatches,
      };

      expect(summaryMatches, ['DEMO-2']);
      expect(descriptionMatches, ['DEMO-4']);
      expect(acceptanceMatches, ['DEMO-5']);
      expect(allMatches.length, 3);
    },
  );
}

String _frontMatterValue(String markdown, String key) {
  final lines = markdown.split('\n');
  if (lines.isEmpty || lines.first.trim() != '---') {
    return '';
  }
  for (var index = 1; index < lines.length; index += 1) {
    final line = lines[index];
    if (line.trim() == '---') {
      break;
    }
    if (line.startsWith('$key:')) {
      return line.substring('$key:'.length).trim().replaceAll('"', '');
    }
  }
  return '';
}

String _section(String markdown, String heading) {
  final headingMarker = '# $heading';
  final start = markdown.indexOf(headingMarker);
  if (start == -1) {
    return '';
  }
  final contentStart = markdown.indexOf('\n', start);
  if (contentStart == -1) {
    return '';
  }
  final nextHeading = markdown.indexOf('\n# ', contentStart + 1);
  final content = nextHeading == -1
      ? markdown.substring(contentStart + 1)
      : markdown.substring(contentStart + 1, nextHeading);
  return content.trim();
}

List<String> _bulletItems(String markdown) =>
    RegExp(r'^\s*-\s+(.+)$', multiLine: true)
        .allMatches(markdown)
        .map((match) => match.group(1)!.trim())
        .toList(growable: false);
