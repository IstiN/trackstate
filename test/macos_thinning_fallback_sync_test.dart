import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'macOS reusable workflow thinning fallback matches the helper script',
    () {
      final scriptPath =
          '${Directory.current.path}/tool/check_macos_thinning_fallback_sync.sh';
      final result = Process.runSync(
        'bash',
        [scriptPath],
        workingDirectory: Directory.current.path,
        includeParentEnvironment: true,
        runInShell: false,
      );

      expect(
        result.exitCode,
        0,
        reason:
            'Fallback drift detected:\n${result.stdout}\n${result.stderr}',
      );
    },
  );
}
