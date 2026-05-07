import 'dart:convert';
import 'dart:io';

import '../../core/models/runtime_startup_observation.dart';

Future<RuntimeOverrideObservation> inspectLocalGitOverrideAttempt() async {
  final flutterExecutable = _resolveFlutterExecutable();
  if (flutterExecutable == null) {
    return const RuntimeOverrideObservation(
      isBlocked: true,
      blockedReason: 'Flutter executable was not available for the override probe.',
    );
  }

  final result = await Process.run(
    flutterExecutable,
    [
      'test',
      'testing/tests/TS-39/support/ts39_runtime_define_override_probe_test.dart',
      '--dart-define=TRACKSTATE_RUNTIME=local-git',
    ],
    workingDirectory: Directory.current.path,
  );

  if (result.exitCode != 0) {
    return RuntimeOverrideObservation(
      isBlocked: true,
      blockedReason:
          'Override probe failed (${result.exitCode}). ${result.stderr}'.trim(),
    );
  }

  final payload = _parseProbePayload(result.stdout.toString());
  if (payload == null) {
    return RuntimeOverrideObservation(
      isBlocked: true,
      blockedReason: 'Override probe completed without a readable payload.',
    );
  }

  return RuntimeOverrideObservation(
    isBlocked: false,
    configuredRuntimeName: payload['configuredRuntimeName'] as String?,
    repositoryType: payload['repositoryType'] as String?,
    usesLocalPersistence: payload['usesLocalPersistence'] as bool?,
    supportsGitHubAuth: payload['supportsGitHubAuth'] as bool?,
  );
}

String? _resolveFlutterExecutable() {
  final flutterRoot = Platform.environment['FLUTTER_ROOT'];
  if (flutterRoot != null && flutterRoot.trim().isNotEmpty) {
    return '$flutterRoot/bin/flutter';
  }
  final path = Platform.environment['PATH'];
  if (path == null || path.trim().isEmpty) {
    return null;
  }
  for (final segment in path.split(Platform.isWindows ? ';' : ':')) {
    final candidate = File(
      '$segment${Platform.pathSeparator}flutter${Platform.isWindows ? '.bat' : ''}',
    );
    if (candidate.existsSync()) {
      return candidate.path;
    }
  }
  return null;
}

Map<String, Object?>? _parseProbePayload(String output) {
  for (final line in const LineSplitter().convert(output)) {
    if (!line.startsWith('TS39_OVERRIDE_RESULT:')) {
      continue;
    }
    final jsonText = line.substring('TS39_OVERRIDE_RESULT:'.length);
    return jsonDecode(jsonText) as Map<String, Object?>;
  }
  return null;
}
