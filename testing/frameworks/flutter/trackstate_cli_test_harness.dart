import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/cli/trackstate_cli.dart';

void main() {
  test('trackstate cli harness', () async {
    final argsFile = _requiredEnvironmentVariable('TRACKSTATE_CLI_ARGS_FILE');
    final stdoutFile = _requiredEnvironmentVariable('TRACKSTATE_CLI_STDOUT_FILE');
    final exitCodeFile = _requiredEnvironmentVariable(
      'TRACKSTATE_CLI_EXIT_CODE_FILE',
    );
    final workingDirectory = _requiredEnvironmentVariable(
      'TRACKSTATE_CLI_WORKING_DIRECTORY',
    );

    final cli = TrackStateCli(
      environment: TrackStateCliEnvironment(
        environment: Platform.environment,
        workingDirectory: workingDirectory,
        resolvePath: (path) => _resolvePath(
          path: path,
          workingDirectory: workingDirectory,
        ),
        readGhAuthToken: () async {
          try {
            final result = await Process.run('gh', ['auth', 'token']);
            if (result.exitCode != 0) {
              return null;
            }
            return result.stdout.toString().trim();
          } on ProcessException {
            return null;
          }
        },
      ),
    );

    final execution = await cli.run(await _readArguments(argsFile));

    await File(stdoutFile).writeAsString(execution.stdout, flush: true);
    await File(exitCodeFile).writeAsString(
      execution.exitCode.toString(),
      flush: true,
    );
  });
}

String _requiredEnvironmentVariable(String name) {
  final value = Platform.environment[name];
  if (value == null || value.isEmpty) {
    throw StateError('Missing required environment variable: $name');
  }
  return value;
}

Future<List<String>> _readArguments(String path) async {
  final bytes = await File(path).readAsBytes();
  if (bytes.isEmpty) {
    return const <String>[];
  }

  final arguments = <String>[];
  final current = <int>[];
  for (final byte in bytes) {
    if (byte == 0) {
      arguments.add(String.fromCharCodes(current));
      current.clear();
      continue;
    }
    current.add(byte);
  }
  if (current.isNotEmpty) {
    arguments.add(String.fromCharCodes(current));
  }
  return arguments;
}

String _resolvePath({required String path, required String workingDirectory}) {
  final uri = Uri.file(workingDirectory.endsWith('/') ? workingDirectory : '$workingDirectory/');
  return uri.resolve(path).toFilePath();
}
