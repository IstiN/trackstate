import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('theme token check accepts lib directory targets', () async {
    final result = await Process.run(_dartExecutable(), [
      'run',
      'tool/check_theme_tokens.dart',
      'lib/',
    ], workingDirectory: Directory.current.path);

    final output = '${result.stdout}${result.stderr}';

    expect(
      result.exitCode,
      0,
      reason:
          'Expected `dart run tool/check_theme_tokens.dart lib/` to succeed.\n'
          'stdout:\n${result.stdout}\n'
          'stderr:\n${result.stderr}',
    );
    expect(output, contains('No theme token policy violations found.'));
    expect(output.toLowerCase(), isNot(contains('warning •')));
  });
}

String _dartExecutable() {
  final flutterRoot = Platform.environment['FLUTTER_ROOT'];
  if (flutterRoot != null && flutterRoot.isNotEmpty) {
    return '$flutterRoot/bin/dart';
  }
  return 'dart';
}
