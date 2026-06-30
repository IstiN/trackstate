import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'flutter analyze flags weakened workspace sync semantic getters that drop sync error context',
    timeout: const Timeout(Duration(minutes: 2)),
    () async {
      final tempDir = await Directory.systemTemp.createTemp(
        'trackstate-semantic-label-lint',
      );
      addTearDown(() => tempDir.delete(recursive: true));

      await _copyRepository(source: Directory.current, destination: tempDir);

      final targetFile = File(
        '${tempDir.path}/lib/ui/features/tracker/views/trackstate_app_widgets_workspace.dart',
      );
      final source = targetFile.readAsStringSync();
      final mutatedSource = source.replaceFirst(
        ').workspaceSyncAttentionNeededSemanticLabel;',
        ').workspaceSyncAttentionNeededVisibleLabel;',
      );

      expect(
        mutatedSource,
        isNot(equals(source)),
        reason:
            'Expected the test mutation to weaken the sync semantic-label '
            'localization getter.',
      );
      targetFile.writeAsStringSync(mutatedSource);

      final result = await Process.run(_flutterBinary(), <String>[
        'analyze',
        'lib/ui/features/tracker/views/trackstate_app_widgets_workspace.dart',
      ], workingDirectory: tempDir.path);

      final output = '${result.stdout}${result.stderr}';

      expect(
        output.toLowerCase(),
        isNot(contains('no issues found!')),
        reason:
            'Expected flutter analyze to flag the weakened semantic label.\n'
            'stdout:\n${result.stdout}\n'
            'stderr:\n${result.stderr}',
      );
      expect(
        output.toLowerCase(),
        anyOf(
          contains('workspacesyncattentionneededvisiblelabel'),
          contains('_workspacesyncattentionneededvisibletext'),
          contains('semantic'),
          contains("can't be assigned"),
        ),
        reason:
            'Expected the analyzer output to explain the missing sync-error '
            'context.\nstdout:\n${result.stdout}\nstderr:\n${result.stderr}',
      );
    },
  );
}

String _flutterBinary() {
  const configured = String.fromEnvironment('TRACKSTATE_FLUTTER_BIN');
  if (configured.isNotEmpty) {
    return configured;
  }

  final flutterRoot = Platform.environment['FLUTTER_ROOT'];
  if (flutterRoot != null && flutterRoot.isNotEmpty) {
    return '$flutterRoot/bin/flutter';
  }

  return 'flutter';
}

Future<void> _copyRepository({
  required Directory source,
  required Directory destination,
}) async {
  await for (final entity in source.list(recursive: true, followLinks: false)) {
    final relativePath = entity.path.substring(source.path.length + 1);
    if (_shouldSkip(relativePath)) {
      if (entity is Directory) {
        continue;
      }
      continue;
    }

    final destinationPath = '${destination.path}/$relativePath';
    if (entity is Directory) {
      await Directory(destinationPath).create(recursive: true);
      continue;
    }
    if (entity is File) {
      await File(destinationPath).parent.create(recursive: true);
      await entity.copy(destinationPath);
    }
  }
}

bool _shouldSkip(String relativePath) {
  const skippedRoots = <String>{'.git', '.dart_tool', 'build', 'outputs'};
  final normalized = relativePath.replaceAll('\\', '/');
  return skippedRoots.any(
    (root) => normalized == root || normalized.startsWith('$root/'),
  );
}
