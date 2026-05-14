import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  late Directory tempDir;
  late Directory binDir;
  late String scriptPath;

  Future<void> writeExecutable(String name, String body) async {
    final file = File('${binDir.path}/$name');
    await file.writeAsString(body);
    await Process.run('chmod', ['+x', file.path]);
  }

  Future<ProcessResult> runReadinessCheck() {
    return Process.run(
      'bash',
      [scriptPath],
      environment: <String, String>{
        ...Platform.environment,
        'PATH': '${binDir.path}:${Platform.environment['PATH'] ?? ''}',
        'TRACKSTATE_UNAME_S': 'Darwin',
        'TRACKSTATE_UNAME_M': 'arm64',
        'TRACKSTATE_EXPECTED_FLUTTER_VERSION': '3.35.3',
        'TRACKSTATE_EXPECTED_DART_VERSION': '3.9.2',
        'TRACKSTATE_MIN_XCODE_MAJOR': '16',
      },
    );
  }

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp(
      'trackstate-macos-runner-check-',
    );
    binDir = Directory('${tempDir.path}/bin')..createSync();
    scriptPath =
        '${Directory.current.path}/tool/check_macos_release_runner.sh';

    await writeExecutable(
      'flutter',
      '#!/usr/bin/env bash\n'
      'echo "Flutter 3.35.3 • channel stable • fake"\n',
    );
    await writeExecutable(
      'dart',
      '#!/usr/bin/env bash\n'
      'echo "Dart SDK version: 3.9.2 (stable) (Fake)" >&2\n',
    );
    await writeExecutable(
      'xcodebuild',
      '#!/usr/bin/env bash\n'
      'echo "Xcode 16.1"\n'
      'echo "Build version 16B40"\n',
    );
    await writeExecutable(
      'zip',
      '#!/usr/bin/env bash\n'
      'echo "zip"\n',
    );
    await writeExecutable(
      'ditto',
      '#!/usr/bin/env bash\n'
      'echo "ditto"\n',
    );
    await writeExecutable(
      'tar',
      '#!/usr/bin/env bash\n'
      'echo "tar"\n',
    );
    await writeExecutable(
      'shasum',
      '#!/usr/bin/env bash\n'
      'echo "shasum"\n',
    );
  });

  tearDown(() async {
    if (tempDir.existsSync()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('runner readiness script accepts the documented toolchain', () async {
    final result = await runReadinessCheck();

    expect(result.exitCode, 0, reason: '${result.stdout}\n${result.stderr}');
    expect(
      '${result.stdout}',
      contains('Runner readiness verified for Flutter 3.35.3'),
    );
  });

  test('runner readiness script fails when Xcode is too old', () async {
    await writeExecutable(
      'xcodebuild',
      '#!/usr/bin/env bash\n'
      'echo "Xcode 15.4"\n'
      'echo "Build version 15F31d"\n',
    );

    final result = await runReadinessCheck();

    expect(result.exitCode, isNonZero);
    expect(
      '${result.stdout}${result.stderr}',
      contains('Xcode 16 or newer is required'),
    );
  });
}
