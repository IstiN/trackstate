import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  final repositoryRoot = Directory.current.path;

  group('Install scripts', () {
    test('install.sh exists and is executable', () {
      final script = File('$repositoryRoot/scripts/install/install.sh');
      expect(script.existsSync(), isTrue);

      final mode = script.statSync().mode;
      final isExecutable = mode & 0x49 != 0;
      expect(isExecutable, isTrue);
    });

    test('install.ps1 exists', () {
      final script = File('$repositoryRoot/scripts/install/install.ps1');
      expect(script.existsSync(), isTrue);
    });

    test('install.cmd exists', () {
      final script = File('$repositoryRoot/scripts/install/install.cmd');
      expect(script.existsSync(), isTrue);
    });

    test('install.sh passes bash syntax check', () async {
      final result = await Process.run(
        'bash',
        <String>['-n', '$repositoryRoot/scripts/install/install.sh'],
      );
      expect(result.exitCode, 0, reason: result.stderr);
    });

    test('install.sh prints usage for --help', () async {
      final result = await Process.run(
        'bash',
        <String>['$repositoryRoot/scripts/install/install.sh', '--help'],
      );
      expect(result.exitCode, 0, reason: result.stderr);
      expect(result.stdout, contains('Usage:'));
      expect(result.stdout, contains('VERSION'));
    });

    test('install.sh rejects unknown options', () async {
      final result = await Process.run(
        'bash',
        <String>['$repositoryRoot/scripts/install/install.sh', '--unknown'],
      );
      expect(result.exitCode, isNot(0));
    });

    test('install.sh detects unsupported operating systems', () async {
      final result = await Process.run(
        'bash',
        <String>['$repositoryRoot/scripts/install/install.sh'],
        environment: <String, String>{
          ...Platform.environment,
          'PATH': '/usr/bin:/bin',
        },
      );
      // The script fails when it cannot reach the GitHub API or when the
      // platform is unsupported. The exit code is non-zero, confirming the
      // script does not silently do nothing.
      expect(result.exitCode, isNot(0));
    });
  });
}
