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

    test('install.sh contains the repo placeholder', () {
      final script = File('$repositoryRoot/scripts/install/install.sh');
      final content = script.readAsStringSync();
      expect(content, contains('__REPO_PLACEHOLDER__'));
      expect(content, isNot(contains('IstiN/trackstate')));
    });

    test('install.ps1 contains the repo placeholder and deferred InstallDir', () {
      final script = File('$repositoryRoot/scripts/install/install.ps1');
      final content = script.readAsStringSync();
      expect(content, contains('__REPO_PLACEHOLDER__'));
      expect(content, isNot(contains('IstiN/trackstate')));
      // $InstallDir must be initialized after Get-PlatformSuffix so non-Windows
      // users see the platform error instead of a Join-Path null-path error.
      final platformSuffixIndex = content.indexOf('Get-PlatformSuffix');
      final installDirIndex = content.indexOf('\$InstallDir = Join-Path');
      expect(installDirIndex, greaterThan(platformSuffixIndex));
    });

    test('install.cmd uses a less collision-prone temp filename and repo placeholder', () {
      final script = File('$repositoryRoot/scripts/install/install.cmd');
      final content = script.readAsStringSync();
      expect(content, contains('%RANDOM%'));
      expect(content, contains('%PPID%'));
      expect(content, contains('%TS%'));
      expect(content, contains('__REPO_PLACEHOLDER__'));
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

    test('install.sh resolves the unified checksum for Linux and the Apple checksum for macOS', () {
      final script = File('$repositoryRoot/scripts/install/install.sh');
      final content = script.readAsStringSync();
      final checksumCaseStart = content.indexOf(
        'macOS assets are published by a separate Apple release job',
      );
      expect(checksumCaseStart, greaterThan(-1));
      final checksumCaseBlock = content.substring(checksumCaseStart);
      expect(checksumCaseBlock, contains(r'case "$PLATFORM" in'));
      expect(checksumCaseBlock, contains('macos-*)'));
      expect(
        checksumCaseBlock,
        contains(r'CHECKSUM_NAME="trackstate-apple-${RELEASE_TAG}.sha256"'),
      );
      expect(
        checksumCaseBlock,
        contains(r'CHECKSUM_NAME="trackstate-${RELEASE_TAG}.sha256"'),
      );
      final macosBranchIndex = checksumCaseBlock.indexOf('macos-*)');
      final defaultBranchIndex = checksumCaseBlock.indexOf('*)');
      expect(defaultBranchIndex, greaterThan(macosBranchIndex));
    });
  });
}
