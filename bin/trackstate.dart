import 'dart:io';

import 'package:trackstate/cli/trackstate_cli.dart';

Future<void> main(List<String> arguments) async {
  final cli = TrackStateCli(
    environment: TrackStateCliEnvironment(
      environment: Platform.environment,
      workingDirectory: Directory.current.path,
      resolvePath: (path) => Directory(path).absolute.path,
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
  final execution = await cli.run(arguments);
  stdout.writeln(execution.stdout);
  exitCode = execution.exitCode;
}
