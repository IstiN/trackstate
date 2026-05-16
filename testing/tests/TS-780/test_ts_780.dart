import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:trackstate/data/providers/trackstate_provider.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../components/services/repository_sync_check_public_payload_service.dart';
import 'support/ts780_repository_sync_check_fixture.dart';

const String _ticketKey = 'TS-780';
const String _ticketSummary =
    'Serialize RepositorySyncCheck with zero-value load_snapshot_delta';
const String _testFilePath = 'testing/tests/TS-780/test_ts_780.dart';
const String _runCommand =
    'mkdir -p outputs && flutter test testing/tests/TS-780/test_ts_780.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  'Read the ordinary hosted sync payload with no explicit load_snapshot_delta marker.',
  'Read the hosted sync payload produced by the real provider path when load_snapshot_delta=0 is explicitly requested.',
  'Inspect the serialized public payload map for the presence of the load_snapshot_delta key.',
  'Verify the serialized load_snapshot_delta value is exactly 0 and remains distinguishable from omission.',
];

void main() {
  test(
    'TS-780 serializes explicit load_snapshot_delta=0 into the public RepositorySyncCheck payload',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'repository': 'trackstate/trackstate',
        'contract_shape':
            'RepositorySyncCheck(state, signals, changedPaths, hostedSnapshotReloadDirective) -> public payload map',
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final fixture = Ts780RepositorySyncCheckFixture();
      final serializer = RepositorySyncCheckPublicPayloadService();

      try {
        final failures = <String>[];

        final controlCheck = await fixture.readHostedSyncCheck();
        final controlPayload = serializer.serialize(controlCheck);
        final controlPayloadJson = jsonEncode(controlPayload);
        result['control_payload'] = controlPayload;
        result['control_payload_json'] = controlPayloadJson;

        final controlStepPassed =
            controlCheck.signals.contains(
              WorkspaceSyncSignal.hostedRepository,
            ) &&
            !controlPayload.containsKey('load_snapshot_delta') &&
            controlCheck.hostedSnapshotReloadDirective == null;
        final controlObserved =
            'signals=${_formatList(_signalNames(controlCheck.signals))}; '
            'changed_paths=${_formatList(_stringList(controlPayload['changed_paths']))}; '
            'hosted_snapshot_reload_directive=${_directiveLabel(controlCheck.hostedSnapshotReloadDirective)}; '
            'serialized_payload=$controlPayloadJson';
        _recordStep(
          result,
          step: 1,
          status: controlStepPassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: controlObserved,
        );
        if (!controlStepPassed) {
          failures.add(
            'Step 1 failed: the ordinary hosted sync payload did not match the expected no-flag baseline.\n'
            'Observed: $controlObserved',
          );
        }

        final explicitCheck = await fixture.readHostedSyncCheck(
          loadSnapshotDelta: 0,
        );
        final explicitPayload = serializer.serialize(explicitCheck);
        final explicitPayloadJson = jsonEncode(explicitPayload);
        result['explicit_payload'] = explicitPayload;
        result['explicit_payload_json'] = explicitPayloadJson;

        final explicitStepPassed =
            explicitCheck.signals.contains(
              WorkspaceSyncSignal.hostedRepository,
            ) &&
            explicitCheck.hostedSnapshotReloadDirective ==
                HostedSnapshotReloadDirective.disabled;
        final explicitObserved =
            'signals=${_formatList(_signalNames(explicitCheck.signals))}; '
            'changed_paths=${_formatList(_stringList(explicitPayload['changed_paths']))}; '
            'hosted_snapshot_reload_directive=${_directiveLabel(explicitCheck.hostedSnapshotReloadDirective)}; '
            'serialized_payload=$explicitPayloadJson';
        _recordStep(
          result,
          step: 2,
          status: explicitStepPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: explicitObserved,
        );
        if (!explicitStepPassed) {
          failures.add(
            'Step 2 failed: the explicit load_snapshot_delta=0 provider path did not expose the disabled hosted snapshot reload directive before serialization.\n'
            'Observed: $explicitObserved',
          );
        }

        final hasLoadSnapshotDeltaKey = explicitPayload.containsKey(
          'load_snapshot_delta',
        );
        result['serialized_load_snapshot_delta_present'] =
            hasLoadSnapshotDeltaKey;
        final presenceObserved =
            'control_payload=$controlPayloadJson; '
            'explicit_payload=$explicitPayloadJson; '
            'load_snapshot_delta_present=$hasLoadSnapshotDeltaKey';
        _recordStep(
          result,
          step: 3,
          status: hasLoadSnapshotDeltaKey ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: presenceObserved,
        );
        if (!hasLoadSnapshotDeltaKey) {
          failures.add(
            'Step 3 failed: the serialized explicit-false payload omitted the load_snapshot_delta key.\n'
            'Observed: $presenceObserved',
          );
        }

        final serializedLoadSnapshotDelta =
            explicitPayload['load_snapshot_delta'];
        result['load_snapshot_delta'] = serializedLoadSnapshotDelta;
        final payloadsDistinguishable =
            controlPayloadJson != explicitPayloadJson;
        result['payloads_distinguishable'] = payloadsDistinguishable;
        final valueStepPassed =
            serializedLoadSnapshotDelta == 0 && payloadsDistinguishable;
        final valueObserved =
            'serialized_load_snapshot_delta=$serializedLoadSnapshotDelta; '
            'payloads_distinguishable=$payloadsDistinguishable; '
            'control_payload=$controlPayloadJson; '
            'explicit_payload=$explicitPayloadJson';
        _recordStep(
          result,
          step: 4,
          status: valueStepPassed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: valueObserved,
        );
        if (!valueStepPassed) {
          failures.add(
            'Step 4 failed: the serialized explicit-false payload did not expose load_snapshot_delta as the exact numeric value 0 and distinct from omission.\n'
            'Observed: $valueObserved',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the serialized payloads exactly as an integrated client would consume them and confirmed the no-flag payload omitted load_snapshot_delta while the explicit-false payload showed it at the top level.',
          observed:
              'control_payload=$controlPayloadJson; explicit_payload=$explicitPayloadJson',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the explicit-false payload preserved a numeric zero rather than dropping the field or converting it to a string.',
          observed:
              'explicit_payload_value=${explicitPayload['load_snapshot_delta']}; runtime_type=${explicitPayload['load_snapshot_delta']?.runtimeType}',
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
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
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

void _writePassOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  if (_bugDescriptionFile.existsSync()) {
    _bugDescriptionFile.deleteSync();
  }
  _resultFile.writeAsStringSync(
    '${jsonEncode(const <String, Object>{'status': 'passed', 'passed': 1, 'failed': 0, 'skipped': 0, 'summary': '1 passed, 0 failed'})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
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
    '* Executed the production GitHub hosted-sync compare path twice: once without any explicit marker and once with {noformat}load_snapshot_delta=0{noformat} in the compare commit message.',
    '* Serialized the returned public {noformat}RepositorySyncCheck{noformat} contract through the reusable testing payload service used by this ticket.',
    '* Verified the explicit-false payload preserved a top-level {noformat}load_snapshot_delta{noformat} field with the numeric value {noformat}0{noformat}.',
    '* Compared the serialized no-flag and explicit-false payloads to confirm omission and zero remain distinguishable for integrated clients.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the serialized public payload explicitly contained {noformat}load_snapshot_delta=0{noformat} for the explicit-false path and omitted the field for the no-flag path.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository: {noformat}${result['repository'] ?? '<missing>'}{noformat}',
    '* Control payload: {noformat}${result['control_payload_json'] ?? '<missing>'}{noformat}',
    '* Explicit-false payload: {noformat}${result['explicit_payload_json'] ?? '<missing>'}{noformat}',
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

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $statusLabel',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '## What was automated',
    '- Exercised the production GitHub hosted-sync compare flow with a normal hosted sync and an explicit `load_snapshot_delta=0` hosted sync.',
    '- Serialized the resulting public `RepositorySyncCheck` contract with the ticket-specific testing payload service.',
    '- Verified the explicit-false payload includes a top-level `load_snapshot_delta` field with the numeric value `0`.',
    '- Verified the no-flag payload omits that field so integrated clients can distinguish omission from explicit zero.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the explicit-false public payload serialized as `{"load_snapshot_delta":0}` at the top level while the no-flag payload left the field absent.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '## Observed payloads',
    '- Control payload: `${result['control_payload_json'] ?? '<missing>'}`',
    '- Explicit-false payload: `${result['explicit_payload_json'] ?? '<missing>'}`',
    '',
    '## Test file',
    '```text',
    _testFilePath,
    '```',
    '',
    '## How to run',
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

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey')
    ..writeln()
    ..writeln(
      passed
          ? 'Passed: the serialized public RepositorySyncCheck payload preserved `load_snapshot_delta=0` for the explicit-false hosted sync path.'
          : 'Failed: the serialized public RepositorySyncCheck payload did not preserve the explicit `load_snapshot_delta=0` signal as required.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Control payload: `${result['control_payload_json'] ?? '<missing>'}`',
    )
    ..writeln(
      'Explicit-false payload: `${result['explicit_payload_json'] ?? '<missing>'}`',
    )
    ..writeln(
      'Observed load_snapshot_delta: `${result['load_snapshot_delta'] ?? '<missing>'}`',
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

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'Serializing the public RepositorySyncCheck payload does not preserve the explicit `load_snapshot_delta=0` signal in a way that integrated clients can reliably distinguish from omission.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the explicit-false hosted sync serializes a public payload that contains a top-level `load_snapshot_delta` key with the numeric value `0`, while the no-flag hosted sync omits that key.',
    '- **Actual:** ${_actualResultLine(result)}',
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
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '- Repository: `${result['repository'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Control payload: ${result['control_payload_json'] ?? '<missing>'}',
    'Explicit-false payload: ${result['explicit_payload_json'] ?? '<missing>'}',
    'Observed load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
    'Step details:',
    ..._bugLogLines(result),
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return <String>[
    for (final step in steps)
      '* Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  Observed: {noformat}${step['observed']}{noformat}',
  ];
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return <String>[
    for (final step in steps)
      '- Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  - Observed: `${step['observed']}`',
  ];
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const <String>['* No additional human-style checks were recorded.'];
  }
  return <String>[
    for (final check in checks)
      '* ${check['check']}\n  Observed: {noformat}${check['observed']}{noformat}',
  ];
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const <String>['- No additional human-style checks were recorded.'];
  }
  return <String>[
    for (final check in checks)
      '- ${check['check']}\n  - Observed: `${check['observed']}`',
  ];
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return <String>['1. No step logs were recorded before the failure.'];
  }
  return <String>[
    for (final step in steps)
      '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
          '   - Observed: `${step['observed']}`',
  ];
}

List<String> _bugLogLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>['<no step logs recorded>'];
  }
  return <String>[
    for (final step in steps)
      'Step ${step['step']} [${step['status']}]: ${step['action']} :: ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  return 'the control payload serialized as `${result['control_payload_json'] ?? '<missing>'}` and the explicit-false payload serialized as `${result['explicit_payload_json'] ?? '<missing>'}` instead of exposing a distinct top-level `load_snapshot_delta: 0` field for the explicit-false path.';
}

List<String> _signalNames(Set<WorkspaceSyncSignal> signals) =>
    signals.map((signal) => signal.name).toList(growable: false)..sort();

String _directiveLabel(HostedSnapshotReloadDirective? directive) {
  return switch (directive) {
    HostedSnapshotReloadDirective.enabled => 'enabled',
    HostedSnapshotReloadDirective.disabled => 'disabled',
    null => '<absent>',
  };
}

List<String> _stringList(Object? value) {
  if (value is List<String>) {
    return value;
  }
  if (value is List) {
    return value.map((item) => '$item').toList(growable: false);
  }
  return value == null ? const <String>[] : <String>['$value'];
}

String _formatList(List<String> items) {
  if (items.isEmpty) {
    return '<empty>';
  }
  return items.join('|');
}
