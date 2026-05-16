import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/interfaces/repository_sync_check_driver.dart';
import '../../frameworks/api/github/github_repository_sync_check_framework.dart';

const String _ticketKey = 'TS-780';
const String _ticketSummary =
    'Serialize RepositorySyncCheck with zero-value load_snapshot_delta';
const String _testFilePath = 'testing/tests/TS-780/test_ts_780.dart';
const String _runCommand =
    'mkdir -p outputs && flutter test testing/tests/TS-780/test_ts_780.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Read the ordinary hosted sync payload with no explicit load_snapshot_delta marker.',
  'Read the hosted sync payload produced by the real provider path when load_snapshot_delta=0 is explicitly requested.',
  'Invoke the production JSON serialization path for the public RepositorySyncCheck contract and inspect the generated payload.',
  'Verify the serialized explicit-false payload keeps load_snapshot_delta=0 and stays distinguishable from omission.',
];

void main() {
  test(
    'TS-780 serializes explicit load_snapshot_delta=0 through the shipped RepositorySyncCheck JSON path',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'repository': 'trackstate/trackstate',
        'contract_shape':
            'RepositorySyncCheck -> jsonEncode(...) -> public payload map',
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final RepositorySyncCheckDriver driver =
          await GitHubRepositorySyncCheckFramework.create();

      try {
        final failures = <String>[];

        final controlCheck = await driver.readHostedSyncCheck();
        final controlContractObservation = _describeSyncCheck(controlCheck);
        result['control_contract'] = controlContractObservation;
        final controlStepPassed =
            controlCheck.signals.contains(
              WorkspaceSyncSignal.hostedRepository,
            ) &&
            controlCheck.hostedSnapshotReloadDirective == null;
        _recordStep(
          result,
          step: 1,
          status: controlStepPassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: controlContractObservation,
        );
        if (!controlStepPassed) {
          failures.add(
            'Step 1 failed: the ordinary hosted sync did not expose the expected control RepositorySyncCheck contract.\n'
            'Observed: $controlContractObservation',
          );
        }

        final explicitCheck = await driver.readHostedSyncCheck(
          loadSnapshotDelta: 0,
        );
        final explicitContractObservation = _describeSyncCheck(explicitCheck);
        result['explicit_contract'] = explicitContractObservation;
        final explicitStepPassed =
            explicitCheck.signals.contains(
              WorkspaceSyncSignal.hostedRepository,
            ) &&
            explicitCheck.hostedSnapshotReloadDirective ==
                HostedSnapshotReloadDirective.disabled;
        _recordStep(
          result,
          step: 2,
          status: explicitStepPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: explicitContractObservation,
        );
        if (!explicitStepPassed) {
          failures.add(
            'Step 2 failed: the explicit load_snapshot_delta=0 hosted sync did not expose HostedSnapshotReloadDirective.disabled before serialization.\n'
            'Observed: $explicitContractObservation',
          );
        }

        final controlSerialization = _attemptProductionSerialization(
          controlCheck,
        );
        final explicitSerialization = _attemptProductionSerialization(
          explicitCheck,
        );

        result['control_serialization'] = controlSerialization.describe();
        result['explicit_serialization'] = explicitSerialization.describe();

        final controlSerializationPassed =
            controlSerialization.error == null &&
            controlSerialization.payload != null &&
            !controlSerialization.payload!.containsKey('load_snapshot_delta');
        _recordStep(
          result,
          step: 3,
          status: controlSerializationPassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'control_serialization=${controlSerialization.describe()}; '
              'explicit_serialization=${explicitSerialization.describe()}',
        );
        if (!controlSerializationPassed) {
          failures.add(
            'Step 3 failed: the shipped JSON serialization path did not expose a usable public payload for the control RepositorySyncCheck.\n'
            'Observed control serialization: ${controlSerialization.describe()}\n'
            'Observed explicit serialization: ${explicitSerialization.describe()}',
          );
        }

        final explicitPayload = explicitSerialization.payload;
        final controlPayload = controlSerialization.payload;
        final payloadsDistinguishable =
            controlSerialization.json != null &&
            explicitSerialization.json != null &&
            controlSerialization.json != explicitSerialization.json;
        result['payloads_distinguishable'] = payloadsDistinguishable;
        result['control_payload_json'] = controlSerialization.json;
        result['explicit_payload_json'] = explicitSerialization.json;
        result['serialized_load_snapshot_delta'] =
            explicitPayload?['load_snapshot_delta'];

        final explicitSerializationPassed =
            explicitSerialization.error == null &&
            explicitPayload != null &&
            explicitPayload['load_snapshot_delta'] == 0 &&
            payloadsDistinguishable &&
            controlPayload != null;
        _recordStep(
          result,
          step: 4,
          status: explicitSerializationPassed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed:
              'control_payload=${controlPayload == null ? '<unavailable>' : jsonEncode(controlPayload)}; '
              'explicit_payload=${explicitPayload == null ? '<unavailable>' : jsonEncode(explicitPayload)}; '
              'payloads_distinguishable=$payloadsDistinguishable; '
              'explicit_serialization=${explicitSerialization.describe()}',
        );
        if (!explicitSerializationPassed) {
          final reason = explicitSerialization.error == null
              ? 'the explicit-false payload did not keep load_snapshot_delta=0 or remained indistinguishable from omission'
              : 'the shipped JSON serialization path failed before exposing a public payload';
          failures.add(
            'Step 4 failed: $reason.\n'
            'Observed control serialization: ${controlSerialization.describe()}\n'
            'Observed explicit serialization: ${explicitSerialization.describe()}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the provider-returned RepositorySyncCheck contract before serialization, the same boundary a production client hands to its serializer.',
          observed:
              'control_contract=$controlContractObservation; explicit_contract=$explicitContractObservation',
        );
        _recordHumanVerification(
          result,
          check:
              'Attempted to serialize the same production contract through Dart\'s shipped JSON encoder instead of a test-owned mapper.',
          observed:
              'control_serialization=${controlSerialization.describe()}; explicit_serialization=${explicitSerialization.describe()}',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

void _recordStep(
  Map<String, Object?> result, {
  required int step,
  required String status,
  required String action,
  required String observed,
}) {
  final steps = result.putIfAbsent('steps', () => <Map<String, Object?>>[]);
  (steps as List<Map<String, Object?>>).add(<String, Object?>{
    'step': step,
    'status': status,
    'action': action,
    'observed': observed,
  });
}

void _recordHumanVerification(
  Map<String, Object?> result, {
  required String check,
  required String observed,
}) {
  final checks = result.putIfAbsent(
    'human_verification',
    () => <Map<String, Object?>>[],
  );
  (checks as List<Map<String, Object?>>).add(<String, Object?>{
    'check': check,
    'observed': observed,
  });
}

String _describeSyncCheck(RepositorySyncCheck syncCheck) {
  return 'signals=${_formatList(_signalNames(syncCheck.signals))}; '
      'changed_paths=${_formatList(syncCheck.changedPaths.toList()..sort())}; '
      'hosted_snapshot_reload_directive=${_directiveLabel(syncCheck.hostedSnapshotReloadDirective)}';
}

SerializationAttempt _attemptProductionSerialization(
  RepositorySyncCheck syncCheck,
) {
  try {
    final serialized = jsonEncode(syncCheck);
    final decoded = jsonDecode(serialized);
    if (decoded is! Map) {
      throw StateError(
        'Production serialization returned ${decoded.runtimeType} instead of a payload map.',
      );
    }
    return SerializationAttempt(
      json: serialized,
      payload: Map<String, Object?>.from(decoded as Map),
    );
  } catch (error) {
    return SerializationAttempt(error: '${error.runtimeType}: $error');
  }
}

void _writePassOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  if (_bugDescriptionFile.existsSync()) {
    _bugDescriptionFile.deleteSync();
  }
  _resultFile.writeAsStringSync(
    '${jsonEncode(const <String, Object>{'status': 'passed', 'passed': 1, 'failed': 0, 'skipped': 0, 'summary': '1 passed, 0 failed'})}\n',
  );
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final lines = <String>[
    passed
        ? 'Removed the test-only payload mapper, moved GitHub provider wiring into `testing/frameworks/api/github/github_repository_sync_check_framework.dart`, and added `testing/tests/TS-780/README.md`.'
        : 'Removed the test-only payload mapper, moved GitHub provider wiring into `testing/frameworks/api/github/github_repository_sync_check_framework.dart`, and added `testing/tests/TS-780/README.md`.',
    '',
    passed
        ? 'New result: the shipped `RepositorySyncCheck` JSON path preserved `load_snapshot_delta=0` for the explicit-false hosted sync and omitted it for the control payload.'
        : 'New result: failed. The real production serialization path still does not expose a usable public `RepositorySyncCheck` payload map for integrated clients.',
  ];
  if (!passed) {
    lines.add('');
    lines.add('Observed error: `${result['error'] ?? '<missing error>'}`');
  }
  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final lines = <String>[
    '## TS-780 rework',
    '',
    '- Replaced the deleted testing-only payload mapper with the shipped JSON serialization attempt (`jsonEncode`) on the real `RepositorySyncCheck` returned by `GitHubTrackStateProvider`.',
    '- Moved `MockClient`/`GitHubTrackStateProvider` wiring out of `testing/tests/TS-780/` into `testing/frameworks/api/github/github_repository_sync_check_framework.dart` behind `RepositorySyncCheckDriver`.',
    '- Added `testing/tests/TS-780/README.md` and updated the ticket config notes.',
    '',
    '## Result',
    '',
    passed
        ? '- ✅ Passed: the production JSON payload preserved `load_snapshot_delta=0` for the explicit-false hosted sync and omitted it for the control path.'
        : '- ❌ Failed: the production JSON serialization surface still cannot expose the `RepositorySyncCheck` payload required by this ticket.',
    '- Control contract: `${result['control_contract'] ?? '<missing>'}`',
    '- Explicit contract: `${result['explicit_contract'] ?? '<missing>'}`',
    '- Control serialization: `${result['control_serialization'] ?? '<missing>'}`',
    '- Explicit serialization: `${result['explicit_serialization'] ?? '<missing>'}`',
    '',
    '## Run',
    '',
    '```bash',
    _runCommand,
    '```',
  ];
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    'h4. Environment',
    '* Repository: {noformat}trackstate/trackstate{noformat}',
    '* Environment: {noformat}flutter test / ${result['os'] ?? 'linux'}{noformat}',
    '* Test file: {noformat}$_testFilePath{noformat}',
    '',
    'h4. Steps to Reproduce',
    '# Create a real {noformat}GitHubTrackStateProvider{noformat} compare-sync check without an explicit {noformat}load_snapshot_delta{noformat} marker.',
    '# Create a second compare-sync check through the same provider path with {noformat}load_snapshot_delta=0{noformat}.',
    '# Pass each returned {noformat}RepositorySyncCheck{noformat} to Dart\'s shipped JSON serializer via {noformat}jsonEncode(syncCheck){noformat}.',
    '# Inspect the serialized payload for a top-level {noformat}load_snapshot_delta{noformat} key.',
    '',
    'h4. Expected Result',
    'The control payload serializes without {noformat}load_snapshot_delta{noformat}, while the explicit-false payload serializes as a public payload map that includes {noformat}load_snapshot_delta: 0{noformat}.',
    '',
    'h4. Actual Result',
    'The provider now exposes the explicit-false directive at the object level, but the shipped serialization path still does not expose a usable public payload map for {noformat}RepositorySyncCheck{noformat}. The JSON encoding attempt fails before any payload with {noformat}load_snapshot_delta{noformat} can be inspected.',
    '* Control contract: {noformat}${result['control_contract'] ?? '<missing>'}{noformat}',
    '* Explicit contract: {noformat}${result['explicit_contract'] ?? '<missing>'}{noformat}',
    '* Control serialization: {noformat}${result['control_serialization'] ?? '<missing>'}{noformat}',
    '* Explicit serialization: {noformat}${result['explicit_serialization'] ?? '<missing>'}{noformat}',
    '',
    'h4. Logs / Error Output',
    '{code}',
    '${result['error'] ?? '<missing error>'}',
    '',
    '${result['traceback'] ?? '<missing traceback>'}',
    '{code}',
    '',
    'h4. Notes',
    '* Missing production capability: {noformat}RepositorySyncCheck{noformat} does not expose a production-owned JSON/map serialization surface that integrated clients can use to observe {noformat}load_snapshot_delta=0{noformat}.',
    '* The reworked TS-780 test no longer uses a testing-only serializer, so this failure reflects a real product-visible gap rather than a test artifact.',
  ];
  return '${lines.join('\n')}\n';
}

String _formatList(List<String> values) {
  if (values.isEmpty) {
    return '<empty>';
  }
  return values.join(',');
}

List<String> _signalNames(Set<WorkspaceSyncSignal> signals) =>
    signals.map((signal) => signal.name).toList(growable: false)..sort();

String _directiveLabel(HostedSnapshotReloadDirective? directive) =>
    switch (directive) {
      HostedSnapshotReloadDirective.enabled => 'enabled',
      HostedSnapshotReloadDirective.disabled => 'disabled',
      null => '<absent>',
    };

final class SerializationAttempt {
  const SerializationAttempt({this.json, this.payload, this.error});

  final String? json;
  final Map<String, Object?>? payload;
  final String? error;

  String describe() {
    if (error != null) {
      return 'error=$error';
    }
    return 'json=${json ?? '<missing>'}; payload=${payload == null ? '<missing>' : jsonEncode(payload)}';
  }
}
