import 'dart:io';

/// Lint: detects direct imports of web-only or native-only packages in files
/// that are NOT conditionally imported.
///
/// Forbidden imports in shared code (non _web.dart / _io.dart / _native.dart):
///   - dart:html (web-only, crashes on mobile/desktop)
///   - dart:js (web-only)
///   - dart:js_util (web-only)
///   - dart:io (native-only, crashes on web)
///
/// These imports are ONLY safe in files that are conditionally imported
/// (e.g., foo_web.dart / foo_io.dart) or in native-only directories.
void main() {
  final libDir = Directory('lib');
  if (!libDir.existsSync()) {
    print('No lib/ directory found.');
    exit(0);
  }

  final forbiddenImports = {
    "dart:html": "web-only (crashes on mobile/desktop)",
    "dart:js'": "web-only",
    "dart:js_util": "web-only",
    "dart:js_interop": "web-only (use conditional import)",
  };

  // Files that are allowed to have platform-specific imports
  bool isExcluded(String path) {
    return path.contains('_web.dart') ||
        path.contains('_io.dart') ||
        path.contains('_native.dart') ||
        path.contains('_stub.dart') ||
        path.contains('_browser.dart') ||
        path.contains('/providers/local/') ||
        path.contains('/bin/') ||
        path.contains('/cli/') ||
        path.contains('_test.dart') ||
        path.contains('/generated/') ||
        path.contains('/tool/');
  }

  final violations = <String>[];

  final dartFiles = libDir
      .listSync(recursive: true)
      .whereType<File>()
      .where((f) => f.path.endsWith('.dart'))
      .where((f) => !isExcluded(f.path));

  for (final file in dartFiles) {
    final lines = file.readAsLinesSync();
    final relativePath =
        file.path.startsWith('./') ? file.path.substring(2) : file.path;

    for (var i = 0; i < lines.length; i++) {
      final line = lines[i].trim();
      if (!line.startsWith('import ')) continue;

      // Check for suppression comment
      if (line.contains('// platform-ok') || line.contains('// conditional')) {
        continue;
      }

      for (final entry in forbiddenImports.entries) {
        if (line.contains("'${entry.key}'") ||
            line.contains('"${entry.key}"')) {
          violations.add(
              '$relativePath:${i + 1}: imports ${entry.key} (${entry.value}) '
              'in shared code — use conditional import pattern');
        }
      }
    }
  }

  if (violations.isEmpty) {
    print('No dead import violations found.');
    exit(0);
  }

  print('⚠️  Dead import violations (${violations.length}):');
  print('');
  for (final v in violations) {
    print('  $v');
  }
  print('');
  print('Fix: Use conditional imports (file_web.dart / file_io.dart pattern).');
  print('Suppress: Add // platform-ok comment on the import line.');
  exit(1);
}
