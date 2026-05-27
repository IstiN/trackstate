import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  late Directory tempDir;
  late Directory binDir;
  late Directory appBundleDir;
  late File operationsLogFile;
  late String helperScriptPath;

  Future<void> writeExecutable(String name, String body) async {
    final file = File('${binDir.path}/$name');
    await file.writeAsString(body);
    final chmodResult = await Process.run('/bin/chmod', ['+x', file.path]);
    expect(chmodResult.exitCode, 0, reason: '${chmodResult.stderr}');
  }

  Future<ProcessResult> runHelper(String command) {
    return Process.run(
      'bash',
      <String>[
        '-lc',
        'set -euo pipefail\n'
            'source "\$HELPER_SCRIPT"\n'
            '$command\n',
      ],
      workingDirectory: tempDir.path,
      environment: <String, String>{
        ...Platform.environment,
        'HELPER_SCRIPT': helperScriptPath,
        'PATH': '${binDir.path}:${Platform.environment['PATH'] ?? ''}',
        'OPERATIONS_LOG': operationsLogFile.path,
      },
    );
  }

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp(
      'trackstate-build-native-release-artifacts-',
    );
    binDir = Directory('${tempDir.path}/bin')..createSync();
    appBundleDir = Directory('${tempDir.path}/TrackState.app/Contents/MacOS')
      ..createSync(recursive: true);
    operationsLogFile = File('${tempDir.path}/operations.log');
    helperScriptPath =
        '${Directory.current.path}/tool/thin_macos_app_bundle.sh';

    await writeExecutable('file', r'''#!/usr/bin/env bash
target="$1"
content="$(cat "$target")"
if [[ "$content" == *"UNIVERSAL_MACHO"* ]]; then
  echo "$target: Mach-O universal binary with 2 architectures"
elif [[ "$content" == *"ARM64_MACHO"* ]]; then
  echo "$target: Mach-O 64-bit executable arm64"
else
  echo "$target: ASCII text"
fi
''');
    await writeExecutable('stat', r'''#!/usr/bin/env bash
if [[ "$1" != "-f" || "$2" != "%Lp" ]]; then
  echo "unexpected stat arguments: $*" >&2
  exit 1
fi
echo "stat:$3" >> "$OPERATIONS_LOG"
printf '755\n'
''');
    await writeExecutable('chmod', r'''#!/usr/bin/env bash
if [[ "$1" == --reference=* ]]; then
  echo "GNU --reference is not supported" >&2
  exit 1
fi
echo "chmod:$1:$2" >> "$OPERATIONS_LOG"
/bin/chmod "$1" "$2"
''');
    await writeExecutable('lipo', r'''#!/usr/bin/env bash
if [[ "$1" != "-thin" || "$2" != "arm64" || "$4" != "-output" ]]; then
  echo "unexpected lipo arguments: $*" >&2
  exit 1
fi
echo "lipo:$3:$5" >> "$OPERATIONS_LOG"
printf "ARM64_MACHO" > "$5"
''');
  });

  tearDown(() async {
    if (tempDir.existsSync()) {
      await tempDir.delete(recursive: true);
    }
  });

  test(
    'workflow sources the reusable macOS app thinning helper before packaging',
    () {
      final workflow = _buildNativeWorkflow();

      expect(workflow, contains('source ./tool/thin_macos_app_bundle.sh'));
      expect(workflow, contains('thin_app_bundle_to_arm64 "\$app_path"'));
    },
  );

  test(
    'thinning helper preserves file mode with macOS-compatible stat and chmod',
    () async {
      final executable = File('${appBundleDir.path}/TrackState');
      await executable.writeAsString('UNIVERSAL_MACHO');
      await Process.run('/bin/chmod', ['755', executable.path]);

      final result = await runHelper(
        'thin_macho_to_arm64 "${executable.path}"',
      );

      expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');
      expect(await executable.readAsString(), 'ARM64_MACHO');
      expect(
        await operationsLogFile.readAsString(),
        allOf(
          contains('lipo:${executable.path}:${executable.path}.arm64'),
          contains('stat:${executable.path}'),
          contains('chmod:755:${executable.path}.arm64'),
        ),
      );
    },
  );

  test(
    'thinning helper rewrites each universal Mach-O in the app bundle and skips non Mach-O files',
    () async {
      final appBundleRoot = Directory('${tempDir.path}/TrackState.app');
      final appExecutable = File('${appBundleDir.path}/TrackState');
      final helperBinary = File('${appBundleDir.path}/trackstate_helper');
      final readme = File('${appBundleDir.path}/README.txt');

      await appExecutable.writeAsString('UNIVERSAL_MACHO');
      await helperBinary.writeAsString('UNIVERSAL_MACHO');
      await readme.writeAsString('plain text');

      final result = await runHelper(
        'thin_app_bundle_to_arm64 "${appBundleRoot.path}"',
      );

      expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');
      expect(await appExecutable.readAsString(), 'ARM64_MACHO');
      expect(await helperBinary.readAsString(), 'ARM64_MACHO');
      expect(await readme.readAsString(), 'plain text');

      final log = await operationsLogFile.readAsString();
      expect(
        log,
        contains('lipo:${appExecutable.path}:${appExecutable.path}.arm64'),
      );
      expect(
        log,
        contains('lipo:${helperBinary.path}:${helperBinary.path}.arm64'),
      );
      expect(log, isNot(contains('README.txt')));
    },
  );
}

String _buildNativeWorkflow() {
  const workflowPathFromDefine = String.fromEnvironment(
    'BUILD_NATIVE_WORKFLOW_PATH',
  );
  final workflowPath = workflowPathFromDefine.isNotEmpty
      ? workflowPathFromDefine
      : Platform.environment['BUILD_NATIVE_WORKFLOW_PATH'] ??
            '.github/workflows/build-native.yml';
  return File(workflowPath).readAsStringSync();
}
