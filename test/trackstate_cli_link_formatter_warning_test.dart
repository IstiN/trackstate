import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'formatter warns to stderr for non-canonical blocks inward link metadata',
    () async {
      final probeRoot = Directory(
        '${Directory.current.path}/testing/tests/TS-644/dart_probe',
      );

      final result = await Process.run(_resolveDartBinary(), <String>[
        '--disable-analytics',
        'run',
        'bin/ts644_link_formatter_warning_probe.dart',
      ], workingDirectory: probeRoot.path);

      expect(
        result.exitCode,
        0,
        reason: 'stdout:\n${result.stdout}\n\nstderr:\n${result.stderr}',
      );

      final payload = jsonDecode(result.stdout as String) as Map<String, Object?>;
      expect(payload['status'], 'passed', reason: result.stdout as String);
      expect(
        payload['observedLinkPayload'],
        <String, String>{
          'type': 'blocks',
          'target': 'TS-2',
          'direction': 'inward',
        },
      );

      final stderr = (result.stderr as String).toLowerCase();
      expect(stderr, contains('warning'));
      expect(stderr, contains('blocks'));
      expect(stderr, contains('inward'));
      expect(stderr, contains('outward'));
    },
  );
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
