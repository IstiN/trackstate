import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../components/services/workspace_profile_store_persistence_inspector.dart';

const String _ticketKey = 'TS-664';
const String _ticketSummary =
    'Persist workspace profile — fields and deterministic ID are stored correctly';
const String _repository = 'owner/repo';
const String _firstBranch = 'main';
const String _secondBranch = 'develop';
final DateTime _fixedClock = DateTime.utc(2026, 5, 14, 1, 5, 24);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  test(
    'TS-664 persists hosted workspace profiles with deterministic branch-specific ids',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'environment': 'flutter service test',
        'os': Platform.operatingSystem,
        'storage_key': WorkspaceProfileStorePersistenceInspector.storageKey,
        'repository': _repository,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      try {
        final inspector = WorkspaceProfileStorePersistenceInspector(
          now: () => _fixedClock,
        );
        final observation = await inspector.observeHostedPersistence(
          repository: _repository,
          firstDefaultBranch: _firstBranch,
          secondDefaultBranch: _secondBranch,
        );

        result['initial_storage_value'] = observation.initialStorageValue;
        result['first_workspace_id'] = observation.firstProfile.id;
        result['second_workspace_id'] = observation.secondProfile.id;
        result['first_store_json'] = const JsonEncoder.withIndent(
          '  ',
        ).convert(observation.afterFirstCreate.state);
        result['second_store_json'] = const JsonEncoder.withIndent(
          '  ',
        ).convert(observation.afterSecondCreate.state);

        final expectedFirstId = workspaceProfileId(
          targetType: WorkspaceProfileTargetType.hosted,
          target: _repository,
          defaultBranch: _firstBranch,
          writeBranch: _firstBranch,
        );
        final expectedSecondId = workspaceProfileId(
          targetType: WorkspaceProfileTargetType.hosted,
          target: _repository,
          defaultBranch: _secondBranch,
          writeBranch: _secondBranch,
        );
        final expectedTimestamp = _fixedClock.toUtc().toIso8601String();

        final failures = <String>[];

        final step1Failure = observation.initialStorageValue != null
            ? 'Step 1 failed: mock device storage was not empty before the WorkspaceProfileService scenario started.\n'
                  'Observed initial storage value:\n'
                  '${observation.initialStorageValue}'
            : null;
        _recordStep(
          result,
          step: 1,
          status: step1Failure == null ? 'passed' : 'failed',
          action: 'Initialize WorkspaceProfileService.',
          observed:
              'storage_key=${WorkspaceProfileStorePersistenceInspector.storageKey}; initial_storage_empty=${observation.initialStorageValue == null}',
        );
        if (step1Failure != null) {
          failures.add(step1Failure);
        }

        final step2Failure = _validateFirstCreate(
          observation,
          expectedFirstId: expectedFirstId,
        );
        _recordStep(
          result,
          step: 2,
          status: step2Failure == null ? 'passed' : 'failed',
          action:
              "Create a hosted workspace profile for 'owner/repo' with defaultBranch 'main'.",
          observed:
              'created_workspace_id=${observation.firstProfile.id}; active_workspace_id=${observation.afterFirstCreate.activeWorkspaceId}; profiles_saved=${observation.afterFirstCreate.profiles.length}',
        );
        if (step2Failure != null) {
          failures.add(step2Failure);
        }

        final step3Failure = _validateStoredMainEntry(
          observation,
          expectedFirstId: expectedFirstId,
          expectedTimestamp: expectedTimestamp,
        );
        _recordStep(
          result,
          step: 3,
          status: step3Failure == null ? 'passed' : 'failed',
          action:
              'Inspect the stored entry in device storage (WorkspaceProfileStore).',
          observed: _describeStoredProfile(
            observation.afterFirstCreate.profileById(expectedFirstId),
          ),
        );
        if (step3Failure != null) {
          failures.add(step3Failure);
        }

        final step4Failure = _validateSecondCreate(
          observation,
          expectedSecondId: expectedSecondId,
        );
        _recordStep(
          result,
          step: 4,
          status: step4Failure == null ? 'passed' : 'failed',
          action:
              "Create a second profile for the same 'owner/repo' but with defaultBranch 'develop'.",
          observed:
              'created_workspace_id=${observation.secondProfile.id}; active_workspace_id=${observation.afterSecondCreate.activeWorkspaceId}; profiles_saved=${observation.afterSecondCreate.profiles.length}',
        );
        if (step4Failure != null) {
          failures.add(step4Failure);
        }

        final step5Failure = _validateIdComparison(
          observation,
          expectedFirstId: expectedFirstId,
          expectedSecondId: expectedSecondId,
          expectedTimestamp: expectedTimestamp,
        );
        _recordStep(
          result,
          step: 5,
          status: step5Failure == null ? 'passed' : 'failed',
          action: 'Compare the workspaceIds for both entries.',
          observed:
              'main_id=$expectedFirstId; develop_id=$expectedSecondId; stored_profiles=${observation.afterSecondCreate.profiles.map((profile) => profile['id']).join(', ')}',
        );
        if (step5Failure != null) {
          failures.add(step5Failure);
        }

        _recordHumanVerification(
          result,
          check:
              'Inspected the raw SharedPreferences entry exactly as a developer or QA engineer would inspect device storage after saving the first hosted workspace.',
          observed:
              'storage_key=${WorkspaceProfileStorePersistenceInspector.storageKey}; raw_state=${observation.afterFirstCreate.rawJson}',
        );
        _recordHumanVerification(
          result,
          check:
              'Inspected the raw stored state again after saving the develop variant and confirmed both branch-specific hosted workspace entries remained visibly distinct.',
          observed:
              'raw_state=${observation.afterSecondCreate.rawJson}; visible_ids=$expectedFirstId, $expectedSecondId',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      }
    },
  );
}

String? _validateFirstCreate(
  WorkspaceProfileStorePersistenceObservation observation, {
  required String expectedFirstId,
}) {
  if (observation.firstProfile.id != expectedFirstId) {
    return 'Step 2 failed: creating the hosted main workspace did not return the deterministic workspaceId derived from the canonical repository target and default branch.\n'
        'Expected workspaceId: $expectedFirstId\n'
        'Observed workspaceId: ${observation.firstProfile.id}';
  }
  if (observation.afterFirstCreate.activeWorkspaceId != expectedFirstId) {
    return 'Step 2 failed: the stored activeWorkspaceId did not point at the new main workspace.\n'
        'Expected activeWorkspaceId: $expectedFirstId\n'
        'Observed activeWorkspaceId: ${observation.afterFirstCreate.activeWorkspaceId}';
  }
  if (observation.afterFirstCreate.profiles.length != 1) {
    return 'Step 2 failed: the store did not contain exactly one saved workspace after the first create operation.\n'
        'Observed profiles: ${observation.afterFirstCreate.profiles.length}\n'
        'Raw state:\n${observation.afterFirstCreate.rawJson}';
  }
  return null;
}

String? _validateStoredMainEntry(
  WorkspaceProfileStorePersistenceObservation observation, {
  required String expectedFirstId,
  required String expectedTimestamp,
}) {
  final firstStored = observation.afterFirstCreate.profileById(expectedFirstId);
  if (firstStored == null) {
    return 'Step 3 failed: device storage did not contain the saved main workspace entry under workspaceId $expectedFirstId.\n'
        'Raw state:\n${observation.afterFirstCreate.rawJson}';
  }

  final fieldFailures = <String>[];
  _expectStoredField(
    fieldFailures,
    entry: firstStored,
    field: 'id',
    expected: expectedFirstId,
  );
  _expectStoredField(
    fieldFailures,
    entry: firstStored,
    field: 'displayName',
    expected: _repository,
  );
  _expectStoredField(
    fieldFailures,
    entry: firstStored,
    field: 'targetType',
    expected: 'hosted',
  );
  _expectStoredField(
    fieldFailures,
    entry: firstStored,
    field: 'target',
    expected: _repository,
  );
  _expectStoredField(
    fieldFailures,
    entry: firstStored,
    field: 'defaultBranch',
    expected: _firstBranch,
  );
  _expectStoredField(
    fieldFailures,
    entry: firstStored,
    field: 'writeBranch',
    expected: _firstBranch,
  );
  _expectStoredField(
    fieldFailures,
    entry: firstStored,
    field: 'lastOpenedAt',
    expected: expectedTimestamp,
  );
  if (observation.afterFirstCreate.migrationComplete != true) {
    fieldFailures.add(
      'Expected migrationComplete=true, observed ${observation.afterFirstCreate.migrationComplete}.',
    );
  }

  if (fieldFailures.isEmpty) {
    return null;
  }
  return 'Step 3 failed: the stored main workspace entry did not preserve every required field.\n'
      '${fieldFailures.join('\n')}\n'
      'Raw state:\n${observation.afterFirstCreate.rawJson}';
}

String? _validateSecondCreate(
  WorkspaceProfileStorePersistenceObservation observation, {
  required String expectedSecondId,
}) {
  if (observation.secondProfile.id != expectedSecondId) {
    return 'Step 4 failed: creating the hosted develop workspace did not return the deterministic workspaceId derived from the canonical repository target and default branch.\n'
        'Expected workspaceId: $expectedSecondId\n'
        'Observed workspaceId: ${observation.secondProfile.id}';
  }
  if (observation.afterSecondCreate.activeWorkspaceId != expectedSecondId) {
    return 'Step 4 failed: the stored activeWorkspaceId did not move to the develop workspace after the second create operation.\n'
        'Expected activeWorkspaceId: $expectedSecondId\n'
        'Observed activeWorkspaceId: ${observation.afterSecondCreate.activeWorkspaceId}';
  }
  if (observation.afterSecondCreate.profiles.length != 2) {
    return 'Step 4 failed: the store did not contain both saved workspace entries after creating the develop variant.\n'
        'Observed profiles: ${observation.afterSecondCreate.profiles.length}\n'
        'Raw state:\n${observation.afterSecondCreate.rawJson}';
  }
  return null;
}

String? _validateIdComparison(
  WorkspaceProfileStorePersistenceObservation observation, {
  required String expectedFirstId,
  required String expectedSecondId,
  required String expectedTimestamp,
}) {
  if (expectedFirstId == expectedSecondId) {
    return 'Step 5 failed: the deterministic workspaceIds collapsed to the same value even though the default branches differ.\n'
        'Observed id: $expectedFirstId';
  }

  final finalFirst = observation.afterSecondCreate.profileById(expectedFirstId);
  final finalSecond = observation.afterSecondCreate.profileById(
    expectedSecondId,
  );
  if (finalFirst == null || finalSecond == null) {
    return 'Step 5 failed: the final stored state did not keep both deterministic workspaceIds.\n'
        'Expected ids: $expectedFirstId and $expectedSecondId\n'
        'Raw state:\n${observation.afterSecondCreate.rawJson}';
  }

  final fieldFailures = <String>[];
  _expectStoredField(
    fieldFailures,
    entry: finalFirst,
    field: 'displayName',
    expected: '$_repository ($_firstBranch)',
  );
  _expectStoredField(
    fieldFailures,
    entry: finalSecond,
    field: 'id',
    expected: expectedSecondId,
  );
  _expectStoredField(
    fieldFailures,
    entry: finalSecond,
    field: 'displayName',
    expected: '$_repository ($_secondBranch)',
  );
  _expectStoredField(
    fieldFailures,
    entry: finalSecond,
    field: 'targetType',
    expected: 'hosted',
  );
  _expectStoredField(
    fieldFailures,
    entry: finalSecond,
    field: 'target',
    expected: _repository,
  );
  _expectStoredField(
    fieldFailures,
    entry: finalSecond,
    field: 'defaultBranch',
    expected: _secondBranch,
  );
  _expectStoredField(
    fieldFailures,
    entry: finalSecond,
    field: 'writeBranch',
    expected: _secondBranch,
  );
  _expectStoredField(
    fieldFailures,
    entry: finalSecond,
    field: 'lastOpenedAt',
    expected: expectedTimestamp,
  );
  if (observation.firstProfile.id == observation.secondProfile.id) {
    fieldFailures.add(
      'The two created workspace ids were identical: ${observation.firstProfile.id}.',
    );
  }

  if (fieldFailures.isEmpty) {
    return null;
  }
  return 'Step 5 failed: the final stored state did not preserve distinct deterministic branch-specific workspaceIds and fields.\n'
      '${fieldFailures.join('\n')}\n'
      'Raw state:\n${observation.afterSecondCreate.rawJson}';
}

void _expectStoredField(
  List<String> failures, {
  required Map<String, Object?> entry,
  required String field,
  required String expected,
}) {
  final observed = '${entry[field] ?? ''}';
  if (observed != expected) {
    failures.add('Expected $field=$expected, observed $observed.');
  }
}

String _describeStoredProfile(Map<String, Object?>? profile) {
  if (profile == null) {
    return 'stored_profile=<missing>';
  }
  return [
    'id=${profile['id']}',
    'displayName=${profile['displayName']}',
    'targetType=${profile['targetType']}',
    'target=${profile['target']}',
    'defaultBranch=${profile['defaultBranch']}',
    'writeBranch=${profile['writeBranch']}',
    'lastOpenedAt=${profile['lastOpenedAt']}',
  ].join('; ');
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
  final lines = <String>[
    'h3. $_ticketKey ${passed ? 'PASSED' : 'FAILED'}',
    '',
    '*Automation coverage*',
    '* Initialized the production {code}SharedPreferencesWorkspaceProfileService{code} with mock device storage and a fixed UTC clock.',
    "* Created hosted workspace profiles for {code}owner/repo{code} on {code}main{code} and {code}develop{code}, then inspected the raw {code}${WorkspaceProfileStorePersistenceInspector.storageKey}{code} value after each save.",
    '* Verified the stored workspace identifier, display name, target type, repository coordinates, default branch, write branch, and {code}lastOpenedAt{code} values.',
    '',
    '*Observed result*',
    passed
        ? '* Matched the expected result: device storage kept deterministic branch-specific workspaceIds and persisted the required fields for both entries.'
        : '* Did not match the expected result.',
    '* Environment: {noformat}flutter service test / ${Platform.operatingSystem}{noformat}.',
    '',
    '*Step results*',
    ..._stepLines(result, jira: true),
    '',
    '*Human-style verification*',
    ..._humanLines(result, jira: true),
    '',
    '*Stored state snapshots*',
    '{code:json}',
    '${result['first_store_json'] ?? '<missing>'}',
    '{code}',
    '{code:json}',
    '${result['second_store_json'] ?? '<missing>'}',
    '{code}',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '*Exact error*',
      '{code}',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '{code}',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final lines = <String>[
    '## $_ticketKey ${passed ? 'Passed' : 'Failed'}',
    '',
    '### Automation',
    '- Initialized the production `SharedPreferencesWorkspaceProfileService` with mock device storage and a fixed UTC clock.',
    '- Created hosted workspace profiles for `owner/repo` on `main` and `develop`, then inspected the raw `${WorkspaceProfileStorePersistenceInspector.storageKey}` value after each save.',
    '- Verified the stored workspace identifier, display name, target type, repository coordinates, default branch, write branch, and `lastOpenedAt` values.',
    '',
    '### Observed result',
    passed
        ? '- Matched the expected result: device storage kept deterministic branch-specific workspaceIds and persisted the required fields for both entries.'
        : '- Did not match the expected result.',
    '- Environment: `flutter service test` on `${Platform.operatingSystem}`.',
    '',
    '### Step results',
    ..._stepLines(result, jira: false),
    '',
    '### Human-style verification',
    ..._humanLines(result, jira: false),
    '',
    '### Stored state snapshots',
    '```json',
    '${result['first_store_json'] ?? '<missing>'}',
    '```',
    '```json',
    '${result['second_store_json'] ?? '<missing>'}',
    '```',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '### Exact error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final lines = <String>[
    '# $_ticketKey ${passed ? 'passed' : 'failed'}',
    '',
    'Ran a production workspace-profile persistence scenario with mock device storage and inspected the raw serialized store value after saving hosted `owner/repo` workspaces for `main` and `develop`.',
    '',
    '## Observed',
    '- Environment: `flutter service test` on `${Platform.operatingSystem}`',
    '- First workspace id: `${result['first_workspace_id'] ?? '<missing>'}`',
    '- Second workspace id: `${result['second_workspace_id'] ?? '<missing>'}`',
    '- Storage key: `${result['storage_key'] ?? WorkspaceProfileStorePersistenceInspector.storageKey}`',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  return [
    '# TS-664 - Workspace profile store does not persist deterministic branch-specific hosted entries correctly',
    '',
    '## Steps to reproduce',
    '1. Initialize WorkspaceProfileService.',
    '   - ${_statusEmoji(_stepStatus(result, 1))} ${_stepObservation(result, 1)}',
    "2. Create a hosted workspace profile for 'owner/repo' with defaultBranch 'main'.",
    '   - ${_statusEmoji(_stepStatus(result, 2))} ${_stepObservation(result, 2)}',
    '3. Inspect the stored entry in device storage (WorkspaceProfileStore).',
    '   - ${_statusEmoji(_stepStatus(result, 3))} ${_stepObservation(result, 3)}',
    "4. Create a second profile for the same 'owner/repo' but with defaultBranch 'develop'.",
    '   - ${_statusEmoji(_stepStatus(result, 4))} ${_stepObservation(result, 4)}',
    '5. Compare the workspaceIds for both entries.',
    '   - ${_statusEmoji(_stepStatus(result, 5))} ${_stepObservation(result, 5)}',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** the serialized store should keep deterministic branch-specific workspace identifiers plus the required `displayName`, `targetType`, `target`, `defaultBranch`, `writeBranch`, and `lastOpenedAt` fields for both hosted `owner/repo` entries.',
    '- **Actual:** ${result['error'] ?? 'the stored state did not match the expected contract.'}',
    '',
    '## Environment details',
    '- Runtime: `flutter service test`',
    '- OS: `${Platform.operatingSystem}`',
    '- Repository target: `$_repository`',
    '- Storage key: `${result['storage_key'] ?? WorkspaceProfileStorePersistenceInspector.storageKey}`',
    '- First branch: `$_firstBranch`',
    '- Second branch: `$_secondBranch`',
    '',
    '## Screenshots or logs',
    '- Screenshot: `N/A (service test)`',
    '### First stored state',
    '```json',
    '${result['first_store_json'] ?? '<missing>'}',
    '```',
    '### Final stored state',
    '```json',
    '${result['second_store_json'] ?? '<missing>'}',
    '```',
  ].join('\n');
}

List<String> _stepLines(Map<String, Object?> result, {required bool jira}) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  return steps.map((Object? rawStep) {
    final step = rawStep as Map<Object?, Object?>;
    final prefix = jira ? '#' : '-';
    return '$prefix Step ${step['step']} (${step['status']}): ${step['action']} Observed: ${step['observed']}';
  }).toList();
}

List<String> _humanLines(Map<String, Object?> result, {required bool jira}) {
  final checks =
      (result['human_verification'] as List<Object?>?) ?? const <Object?>[];
  return checks.map((Object? rawCheck) {
    final check = rawCheck as Map<Object?, Object?>;
    final prefix = jira ? '#' : '-';
    return '$prefix ${check['check']} Observed: ${check['observed']}';
  }).toList();
}

String _stepStatus(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['status'] ?? 'failed'}';
    }
  }
  return 'failed';
}

String _stepObservation(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['observed'] ?? ''}';
    }
  }
  return '${result['error'] ?? 'No observation captured.'}';
}

String _statusEmoji(String status) => status == 'passed' ? '✅' : '❌';
