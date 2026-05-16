import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import 'support/ts780_repository_sync_check_service_factory.dart';

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

      final syncCheckService = await createTs780RepositorySyncCheckService();

      try {
        final failures = <String>[];

        final controlCheck = await syncCheckService.readHostedSyncCheck();
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

        final explicitCheck = await syncCheckService.readHostedSyncCheck(
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
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
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
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _jiraComment(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was tested',
    '* Executed the production GitHub hosted compare-sync path twice: once without any explicit {noformat}load_snapshot_delta{noformat} marker and once with {noformat}load_snapshot_delta=0{noformat}.',
    '* Observed the real returned {noformat}RepositorySyncCheck{noformat} contract before serialization to confirm the explicit-false directive was present on the model.',
    '* Attempted to serialize both returned contracts through Dart\'s shipped JSON encoder ({noformat}jsonEncode(syncCheck){noformat}) and inspected the resulting client-visible payload or failure.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the no-flag payload omitted {noformat}load_snapshot_delta{noformat}, while the explicit-false payload preserved {noformat}load_snapshot_delta=0{noformat}.'
        : '* Did not match the expected result. The production serialization path still fails before exposing a usable public payload map for {noformat}RepositorySyncCheck{noformat}.',
    '* Environment: {noformat}flutter test / ${result['os'] ?? Platform.operatingSystem}{noformat}',
    '* Repository: {noformat}${result['repository'] ?? 'trackstate/trackstate'}{noformat}',
    '* Control contract: {noformat}${result['control_contract'] ?? '<missing>'}{noformat}',
    '* Explicit contract: {noformat}${result['explicit_contract'] ?? '<missing>'}{noformat}',
    '* Control serialization: {noformat}${result['control_serialization'] ?? '<missing>'}{noformat}',
    '* Explicit serialization: {noformat}${result['explicit_serialization'] ?? '<missing>'}{noformat}',
    '',
    'h4. Step results',
    ..._jiraStepLines(result),
    '',
    'h4. Human-style verification',
    ..._jiraHumanVerificationLines(result),
    '',
    'h4. Test file',
    '{code}',
    _testFilePath,
    '{code}',
    '',
    'h4. Run command',
    '{code:bash}',
    _runCommand,
    '{code}',
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      'h4. Exact error',
      '{noformat}',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '{noformat}',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey')
    ..writeln()
    ..writeln(
      passed
          ? 'Passed: the production serialization boundary preserved `load_snapshot_delta=0` for the explicit-false hosted sync and omitted the field for the control sync.'
          : 'Failed: the production serialization boundary still throws before exposing a client-visible `RepositorySyncCheck` payload map.',
    )
    ..writeln()
    ..writeln(
      'Environment: `flutter test / ${result['os'] ?? Platform.operatingSystem}`',
    )
    ..writeln(
      'Repository: `${result['repository'] ?? 'trackstate/trackstate'}`',
    )
    ..writeln(
      'Control contract: `${result['control_contract'] ?? '<missing>'}`',
    )
    ..writeln(
      'Explicit contract: `${result['explicit_contract'] ?? '<missing>'}`',
    )
    ..writeln(
      'Control serialization: `${result['control_serialization'] ?? '<missing>'}`',
    )
    ..writeln(
      'Explicit serialization: `${result['explicit_serialization'] ?? '<missing>'}`',
    );

  if (!passed) {
    buffer
      ..writeln()
      ..writeln('Error:')
      ..writeln('```text')
      ..writeln('${result['error'] ?? '<missing>'}')
      ..writeln()
      ..writeln('${result['traceback'] ?? '<missing>'}')
      ..writeln('```');
  }

  return buffer.toString();
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $statusLabel',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '## What was automated',
    '- Executed the production GitHub hosted compare-sync path twice: once without any explicit `load_snapshot_delta` marker and once with `load_snapshot_delta=0`.',
    '- Verified the real returned `RepositorySyncCheck` contract before serialization so the test exercises the shipped provider behavior rather than a test-owned mapper.',
    '- Attempted to serialize both returned contracts through Dart\'s shipped JSON encoder and compared the client-visible outcomes.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the no-flag payload omitted `load_snapshot_delta`, while the explicit-false payload preserved `load_snapshot_delta=0`.'
        : '- Did not match the expected result. The production serialization path still fails before exposing a usable public `RepositorySyncCheck` payload map.',
    '',
    '## Key observations',
    '- Control contract: `${result['control_contract'] ?? '<missing>'}`',
    '- Explicit contract: `${result['explicit_contract'] ?? '<missing>'}`',
    '- Control serialization: `${result['control_serialization'] ?? '<missing>'}`',
    '- Explicit serialization: `${result['explicit_serialization'] ?? '<missing>'}`',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '## Test file',
    '```text',
    _testFilePath,
    '```',
    '',
    '## How to run',
    '',
    '```bash',
    _runCommand,
    '```',
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```text',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'The production compare-sync path now exposes the explicit-false reload directive on the in-memory `RepositorySyncCheck`, but the shipped JSON serialization boundary still cannot serialize that contract into a public payload map for integrated clients.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the control payload serializes without `load_snapshot_delta`, while the explicit-false payload serializes as a public payload map that includes `load_snapshot_delta: 0`.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- `RepositorySyncCheck` still lacks a usable production-owned JSON/map serialization surface at this boundary, so integrated clients cannot observe `load_snapshot_delta=0` in the public payload.',
    '- The provider contract distinguishes the explicit-false path in memory (`hosted_snapshot_reload_directive=disabled`) but `jsonEncode(syncCheck)` still throws `JsonUnsupportedObjectError` before any payload map is produced.',
    '',
    '## Exact Error Message or Assertion Failure',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Environment',
    '- URL: local Flutter test execution',
    '- Browser: none',
    '- OS: ${result['os'] ?? Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '- Repository: `${result['repository'] ?? 'trackstate/trackstate'}`',
    '- Test file: `$_testFilePath`',
    '',
    '## Relevant Logs',
    '```text',
    'Control contract: ${result['control_contract'] ?? '<missing>'}',
    'Explicit contract: ${result['explicit_contract'] ?? '<missing>'}',
    'Control serialization: ${result['control_serialization'] ?? '<missing>'}',
    'Explicit serialization: ${result['explicit_serialization'] ?? '<missing>'}',
    'Payloads distinguishable: ${result['payloads_distinguishable'] ?? '<missing>'}',
    'Serialized explicit load_snapshot_delta: ${result['serialized_load_snapshot_delta'] ?? '<missing>'}',
    'Human verification observations:',
    ..._bugHumanVerificationLines(result),
    'Step details:',
    ..._bugLogLines(result),
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '* Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  Observed: {noformat}${step['observed']}{noformat}',
  ];
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '- Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  - Observed: `${step['observed']}`',
  ];
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final check in checks)
      '* ${check['check']}\n'
          '  Observed: {noformat}${check['observed']}{noformat}',
  ];
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final check in checks)
      '- ${check['check']}\n'
          '  - Observed: `${check['observed']}`',
  ];
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>[
      '1. Reproduce the hosted compare-sync control and explicit `load_snapshot_delta=0` paths, then attempt to serialize the resulting `RepositorySyncCheck` contracts.',
    ];
  }
  return [
    for (final step in steps)
      '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
          '   - Observed: ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  final failedSteps =
      ((result['steps'] as List<Map<String, Object?>>?) ?? const [])
          .where((step) => step['status'] != 'passed')
          .toList(growable: false);
  if (failedSteps.isEmpty) {
    return 'No failed steps were recorded, but the test still reported a failure.';
  }

  final details = failedSteps
      .map(
        (step) =>
            'Step ${step['step']} failed while ${step['action']}: ${step['observed']}',
      )
      .join(' ');
  return '$details Control contract: `${result['control_contract'] ?? '<missing>'}`. '
      'Explicit contract: `${result['explicit_contract'] ?? '<missing>'}`. '
      'Control serialization: `${result['control_serialization'] ?? '<missing>'}`. '
      'Explicit serialization: `${result['explicit_serialization'] ?? '<missing>'}`.';
}

List<String> _bugHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const <String>['<no human verification observations recorded>'];
  }
  return [
    for (final check in checks) '${check['check']}: ${check['observed']}',
  ];
}

List<String> _bugLogLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>['<no step details recorded>'];
  }
  return [
    for (final step in steps)
      'Step ${step['step']} [${step['status']}]: ${step['action']} -> ${step['observed']}',
  ];
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
