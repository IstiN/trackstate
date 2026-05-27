import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'data and domain layers remain Flutter-free and the GitHub provider imports package:meta',
    () {
      final disallowedImports = <String>[
        for (final file in _dartFilesIn('lib/data'))
          ..._flutterImportMatches(file),
        for (final file in _dartFilesIn('lib/domain'))
          ..._flutterImportMatches(file),
      ];
      final providerSource = File(
        'lib/data/providers/github/github_trackstate_provider.dart',
      ).readAsStringSync();

      expect(disallowedImports, isEmpty);
      expect(
        providerSource,
        contains("import 'package:meta/"),
      );
      expect(
        providerSource,
        contains("import '../foundation_compat.dart' show kIsWeb;"),
      );
    },
  );
}

Iterable<File> _dartFilesIn(String directoryPath) {
  return Directory(directoryPath)
      .listSync(recursive: true)
      .whereType<File>()
      .where((file) => file.path.endsWith('.dart'));
}

Iterable<String> _flutterImportMatches(File file) sync* {
  final lines = file.readAsLinesSync();
  for (var index = 0; index < lines.length; index += 1) {
    final line = lines[index];
    if (line.contains("import 'package:flutter/")) {
      yield '${file.path}:${index + 1}:$line';
    }
  }
}
