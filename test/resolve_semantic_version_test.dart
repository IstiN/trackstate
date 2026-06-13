import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  final String scriptPath =
      '${Directory.current.path}/tool/resolve_semantic_version.sh';

  ProcessResult runGit(
    List<String> args,
    String workingDirectory, {
    Map<String, String>? environment,
  }) {
    final result = Process.runSync(
      'git',
      args,
      workingDirectory: workingDirectory,
      environment: environment,
      includeParentEnvironment: true,
      runInShell: false,
    );
    if (result.exitCode != 0) {
      fail('git ${args.join(' ')} failed: ${result.stderr}');
    }
    return result;
  }

  ProcessResult runResolver(
    String workingDirectory, {
    required String currentSha,
    List<String> args = const [],
  }) {
    return Process.runSync(
      'bash',
      [scriptPath, ...args],
      workingDirectory: workingDirectory,
      environment: {'CURRENT_SHA': currentSha},
      includeParentEnvironment: true,
      runInShell: false,
    );
  }

  Map<String, String> parseOutput(String output) {
    final entries = <String, String>{};
    for (final line in LineSplitter.split(output)) {
      final index = line.indexOf('=');
      if (index > 0) {
        entries[line.substring(0, index)] = line.substring(index + 1);
      }
    }
    return entries;
  }

  group('resolve_semantic_version.sh', () {
    late Directory tempDir;

    setUp(() {
      tempDir = Directory.systemTemp.createTempSync('resolve-semantic-version-');
      runGit(['init'], tempDir.path);
      runGit(['config', 'user.email', 'test@example.com'], tempDir.path);
      runGit(['config', 'user.name', 'Test User'], tempDir.path);
    });

    tearDown(() {
      tempDir.deleteSync(recursive: true);
    });

    test('resolves v0.0.1 when no semantic version tags exist', () {
      runGit(['commit', '--allow-empty', '-m', 'initial'], tempDir.path);
      final sha = runGit(['rev-parse', 'HEAD'], tempDir.path).stdout.toString().trim();

      final result = runResolver(tempDir.path, currentSha: sha);
      expect(result.exitCode, 0, reason: result.stderr.toString());

      final output = parseOutput(result.stdout.toString());
      expect(output['release_tag'], 'v0.0.1');
      expect(output['release_checkout_ref'], sha);
      expect(output['build_number'], '1');
    });

    test('uses an existing semantic version tag pointing at HEAD', () {
      runGit(['commit', '--allow-empty', '-m', 'initial'], tempDir.path);
      runGit(['tag', 'v1.2.3'], tempDir.path);
      final sha = runGit(['rev-parse', 'HEAD'], tempDir.path).stdout.toString().trim();

      final result = runResolver(tempDir.path, currentSha: sha);
      expect(result.exitCode, 0, reason: result.stderr.toString());

      final output = parseOutput(result.stdout.toString());
      expect(output['release_tag'], 'v1.2.3');
      expect(output['release_checkout_ref'], 'v1.2.3');
    });

    test('patch-bumps the latest semantic version tag', () {
      runGit(['commit', '--allow-empty', '-m', 'initial'], tempDir.path);
      runGit(['tag', 'v1.2.3'], tempDir.path);
      runGit(['commit', '--allow-empty', '-m', 'second'], tempDir.path);
      final sha = runGit(['rev-parse', 'HEAD'], tempDir.path).stdout.toString().trim();

      final result = runResolver(tempDir.path, currentSha: sha);
      expect(result.exitCode, 0, reason: result.stderr.toString());

      final output = parseOutput(result.stdout.toString());
      expect(output['release_tag'], 'v1.2.4');
      expect(output['release_checkout_ref'], sha);
    });

    test('handles leading-zero patch components without octal errors', () {
      runGit(['commit', '--allow-empty', '-m', 'initial'], tempDir.path);
      runGit(['tag', 'v0.0.08'], tempDir.path);
      runGit(['commit', '--allow-empty', '-m', 'second'], tempDir.path);
      final sha = runGit(['rev-parse', 'HEAD'], tempDir.path).stdout.toString().trim();

      final result = runResolver(tempDir.path, currentSha: sha);
      expect(result.exitCode, 0, reason: result.stderr.toString());

      final output = parseOutput(result.stdout.toString());
      expect(output['release_tag'], 'v0.0.9');
      expect(output['release_checkout_ref'], sha);
    });

    test('honors an explicit semantic version release ref', () {
      runGit(['commit', '--allow-empty', '-m', 'initial'], tempDir.path);
      runGit(['tag', 'v9.8.7'], tempDir.path);
      runGit(['commit', '--allow-empty', '-m', 'second'], tempDir.path);
      final sha = runGit(['rev-parse', 'HEAD'], tempDir.path).stdout.toString().trim();

      final result = runResolver(
        tempDir.path,
        currentSha: sha,
        args: ['--release-ref', 'v9.8.7'],
      );
      expect(result.exitCode, 0, reason: result.stderr.toString());

      final output = parseOutput(result.stdout.toString());
      expect(output['release_tag'], 'v9.8.7');
      expect(output['release_checkout_ref'], 'v9.8.7');
    });

    test('rejects a non-semantic explicit release ref', () {
      runGit(['commit', '--allow-empty', '-m', 'initial'], tempDir.path);
      final sha = runGit(['rev-parse', 'HEAD'], tempDir.path).stdout.toString().trim();

      final result = runResolver(
        tempDir.path,
        currentSha: sha,
        args: ['--release-ref', 'not-a-version'],
      );
      expect(result.exitCode, isNonZero);
      expect(result.stderr.toString(), contains('not a semantic version tag'));
    });
  });
}
