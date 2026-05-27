import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('local CLI entrypoint compiles for the Dart runtime', () async {
    final tempDir = await Directory.systemTemp.createTemp(
      'trackstate-cli-compile',
    );
    addTearDown(() => tempDir.delete(recursive: true));

    final outputPath = '${tempDir.path}/trackstate';
    final result = await Process.run(_resolveDartBinary(), <String>[
      'compile',
      'exe',
      'bin/trackstate.dart',
      '-o',
      outputPath,
    ], workingDirectory: Directory.current.path);

    expect(
      result.exitCode,
      0,
      reason: 'stdout:\n${result.stdout}\n\nstderr:\n${result.stderr}',
    );
    expect(
      File(outputPath).existsSync(),
      isTrue,
      reason:
          'Expected the compiled CLI binary at $outputPath.\n'
          'stdout:\n${result.stdout}\n\nstderr:\n${result.stderr}',
    );
  });
}

String _resolveDartBinary() {
  final configured = Platform.environment['TRACKSTATE_DART_BIN'];
  if (configured != null && configured.trim().isNotEmpty) {
    return configured.trim();
  }

  final flutterRoot = Platform.environment['FLUTTER_ROOT'];
  if (flutterRoot != null && flutterRoot.trim().isNotEmpty) {
    final flutterDart = File(
      '${flutterRoot.trim()}/bin/cache/dart-sdk/bin/dart',
    );
    if (flutterDart.existsSync()) {
      return flutterDart.path;
    }
  }

  return 'dart';
}
