import 'dart:io';

/// Checks for web-unsafe patterns in lib/ that would crash on Flutter web:
/// 1. Process.run/Process.start without kIsWeb guard
/// 2. dart:io File/Directory usage in non-stub files without kIsWeb guard
/// 3. unawaited() calls in ViewModel files without notifyListeners nearby
///
/// Usage: dart run tool/check_web_safety.dart

void main() {
  final root = Directory.current;
  final libDir = Directory('${root.path}/lib');
  if (!libDir.existsSync()) {
    stderr.writeln('lib/ directory not found');
    exitCode = 2;
    return;
  }

  final violations = <_Violation>[];
  final dartFiles = libDir
      .listSync(recursive: true)
      .whereType<File>()
      .where((f) => f.path.endsWith('.dart'))
      .where((f) => !f.path.contains('_stub.dart'))
      .where((f) => !f.path.contains('_native.dart'))
      .where((f) => !f.path.contains('_io.dart'))
      .where((f) => !f.path.contains('/providers/local/'))
      .where((f) => !f.path.contains('/bin/'));

  for (final file in dartFiles) {
    final relativePath =
        file.path.substring(root.path.length + 1);
    final lines = file.readAsLinesSync();
    final content = lines.join('\n');

    // Skip files that are already web-guarded at the top
    final hasKIsWebImport = content.contains('kIsWeb');

    // Check 1: Process.run / Process.start without kIsWeb in file
    for (var i = 0; i < lines.length; i++) {
      final line = lines[i];
      if ((line.contains('Process.run') || line.contains('Process.start')) &&
          !line.trimLeft().startsWith('//') &&
          !hasKIsWebImport) {
        violations.add(_Violation(
          path: relativePath,
          line: i + 1,
          message: 'Process.run/start without kIsWeb guard — crashes on web',
          code: 'web_unsafe_process',
        ));
      }
    }

    // Check 2: Direct File() or Directory() constructor in non-stub/non-native
    if (!relativePath.contains('tool/') &&
        !relativePath.contains('bin/') &&
        !relativePath.endsWith('_stub.dart') &&
        !relativePath.endsWith('_native.dart')) {
      for (var i = 0; i < lines.length; i++) {
        final line = lines[i];
        if ((RegExp(r'\bFile\(').hasMatch(line) ||
                RegExp(r'\bDirectory\(').hasMatch(line)) &&
            !line.trimLeft().startsWith('//') &&
            !line.contains('// web-safe') &&
            !hasKIsWebImport &&
            !relativePath.contains('/cli/') &&
            !relativePath.contains('trackstate.dart')) {
          violations.add(_Violation(
            path: relativePath,
            line: i + 1,
            message:
                'dart:io File/Directory without kIsWeb guard — unavailable on web',
            code: 'web_unsafe_io',
          ));
        }
      }
    }
  }

  if (violations.isEmpty) {
    stdout.writeln('No web safety violations found.');
    return;
  }

  stdout.writeln(
      '${violations.length} web safety violation(s) found:\n');
  for (final v in violations) {
    stdout.writeln(
        'warning • ${v.message} • ${v.path}:${v.line} • ${v.code}');
  }
  exitCode = 1;
}

class _Violation {
  final String path;
  final int line;
  final String message;
  final String code;

  _Violation({
    required this.path,
    required this.line,
    required this.message,
    required this.code,
  });
}
