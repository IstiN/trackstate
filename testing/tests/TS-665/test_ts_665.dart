import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/legacy_hosted_workspace_migration_probe.dart';
import 'support/ts665_legacy_hosted_workspace_migration_probe.dart';

const String _ticketKey = 'TS-665';
const String _ticketSummary =
    'First-run migration converts a legacy hosted context into one active workspace with scoped credentials';
const String _testFilePath = 'testing/tests/TS-665/test_ts_665.dart';
const String _runCommand =
    'flutter test testing/tests/TS-665/test_ts_665.dart --reporter expanded';
const String _activeRepository = 'trackstate/trackstate';
const String _unrelatedRepository = 'other/repository';
const String _defaultBranch = 'main';
const String _activeLegacyToken = 'ts665-active-legacy-token';
const String _unrelatedLegacyToken = 'ts665-unrelated-legacy-token';
const String _workspaceTokenPrefix = 'trackstate.githubToken.workspace.';
const String _expectedWorkspaceId = 'hosted:trackstate/trackstate@main';
const String _expectedWorkspaceDisplayName = 'trackstate/trackstate';
const String _expectedLogin = 'demo-user';
const String _expectedDisplayName = 'Demo User';
const String _expectedInitials = 'DU';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets(
    'TS-665 migrates the legacy hosted context during first app launch',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
        'review_fixes': <String>[
          'Launches TrackStateApp with repository unset so the real first-run migration path executes during startup.',
          'Moves SharedPreferences/auth-store orchestration into a layered testing probe under testing/core, testing/components, and testing/frameworks.',
          'Mocks the hosted GitHub backend at the HTTP layer so the migrated hosted session remains connected through the same public startup flow.',
        ],
      };

      final LegacyHostedWorkspaceMigrationProbe probe =
          createTs665LegacyHostedWorkspaceMigrationProbe(tester);

      try {
        final observation = await probe.runScenario(
          activeRepository: _activeRepository,
          defaultBranch: _defaultBranch,
          activeLegacyToken: _activeLegacyToken,
          unrelatedRepository: _unrelatedRepository,
          unrelatedLegacyToken: _unrelatedLegacyToken,
          expectedDisplayName: _expectedDisplayName,
          expectedLogin: _expectedLogin,
          expectedInitials: _expectedInitials,
        );
        final failures = <String>[];
        final expectedWorkspaceTokenKey =
            '$_workspaceTokenPrefix${Uri.encodeComponent(_expectedWorkspaceId)}';
        final workspaceIds = observation.workspaceState.profiles
            .map((profile) => profile.id)
            .toList(growable: false);

        result['workspace_id'] = observation.workspaceState.activeWorkspaceId;
        result['workspace_ids'] = workspaceIds;
        result['workspace_scoped_keys'] = observation.workspaceScopedKeys;
        result['visible_texts'] = observation.visibleTexts;
        result['raw_workspace_state'] =
            observation.rawWorkspaceState ?? '<missing>';

        final step1Observed =
            'active_workspace_id=${observation.workspaceState.activeWorkspaceId}; '
            'workspace_ids=${workspaceIds.join(', ')}; '
            'migration_complete=${observation.workspaceState.migrationComplete}; '
            'display_name=${observation.workspaceState.activeWorkspace?.displayName ?? '<none>'}';
        if (observation.workspaceState.profiles.length != 1 ||
            observation.workspaceState.activeWorkspaceId !=
                _expectedWorkspaceId ||
            !observation.workspaceState.migrationComplete ||
            observation.workspaceState.activeWorkspace?.displayName !=
                _expectedWorkspaceDisplayName) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Launch the production app from an empty workspace-profile store while legacy hosted credentials already exist in SharedPreferences.',
            observed: step1Observed,
          );
          failures.add(
            'Step 1 failed: first launch did not persist exactly one active hosted workspace for $_expectedWorkspaceId.\n'
            'Observed workspace ids: ${workspaceIds.join(', ')}\n'
            'Observed active workspace id: ${observation.workspaceState.activeWorkspaceId}\n'
            'Observed display name: ${observation.workspaceState.activeWorkspace?.displayName ?? '<none>'}\n'
            'Observed migrationComplete: ${observation.workspaceState.migrationComplete}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action:
                'Launch the production app from an empty workspace-profile store while legacy hosted credentials already exist in SharedPreferences.',
            observed: step1Observed,
          );
        }

        final step2Observed =
            'stored_profile_count=${observation.storedProfileCount}; '
            'stored_active_workspace_id=${observation.storedActiveWorkspaceId}; '
            'stored_migration_complete=${observation.storedMigrationComplete}; '
            'raw_workspace_state=${observation.rawWorkspaceState ?? '<missing>'}';
        if (observation.storedProfileCount != 1 ||
            observation.storedActiveWorkspaceId != _expectedWorkspaceId ||
            !observation.storedMigrationComplete) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Observe the persisted workspace-profile store after startup completes.',
            observed: step2Observed,
          );
          failures.add(
            'Step 2 failed: the stored workspace-profile JSON was not normalized to one active migrated workspace.\n'
            'Observed raw state: ${observation.rawWorkspaceState ?? '<missing>'}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action:
                'Observe the persisted workspace-profile store after startup completes.',
            observed: step2Observed,
          );
        }

        final step3Observed =
            'workspace_token=${observation.workspaceToken ?? '<missing>'}; '
            'legacy_active_repository_token=${observation.leftoverActiveLegacyRepositoryToken ?? '<missing>'}; '
            'unrelated_legacy_repository_token=${observation.unrelatedLegacyRepositoryToken ?? '<missing>'}; '
            'workspace_scoped_keys=${observation.workspaceScopedKeys.join(', ')}';
        if (observation.workspaceToken != _activeLegacyToken ||
            observation.leftoverActiveLegacyRepositoryToken != null ||
            observation.unrelatedLegacyRepositoryToken !=
                _unrelatedLegacyToken ||
            observation.workspaceScopedKeys.length != 1 ||
            observation.workspaceScopedKeys.single !=
                expectedWorkspaceTokenKey) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Observe the credential stores after startup migration moves the active hosted token into workspace scope.',
            observed: step3Observed,
          );
          failures.add(
            'Step 3 failed: credential migration did not move only the active repository token into workspace scope.\n'
            'Observed workspace token: ${observation.workspaceToken ?? '<missing>'}\n'
            'Observed leftover active repository token: ${observation.leftoverActiveLegacyRepositoryToken ?? '<missing>'}\n'
            'Observed unrelated repository token: ${observation.unrelatedLegacyRepositoryToken ?? '<missing>'}\n'
            'Observed workspace-scoped keys: ${observation.workspaceScopedKeys.join(', ')}',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Observe the credential stores after startup migration moves the active hosted token into workspace scope.',
            observed: step3Observed,
          );
        }

        final step4Observed =
            'connected_visible=${observation.connectedVisible}; '
            'display_name_visible=${observation.displayNameVisible}; '
            'login_visible=${observation.loginVisible}; '
            'initials_visible=${observation.initialsVisible}; '
            'visible_texts=${observation.visibleTexts.join(' | ')}';
        if (!observation.connectedVisible ||
            !observation.displayNameVisible ||
            !observation.loginVisible ||
            !observation.initialsVisible) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action:
                'Observe the visible hosted identity in the app chrome after first-run migration completes.',
            observed: step4Observed,
          );
          failures.add(
            'Step 4 failed: the first-run app experience did not keep the hosted session visibly connected.\n'
            'Visible texts: ${observation.visibleTexts.join(' | ')}',
          );
        } else {
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action:
                'Observe the visible hosted identity in the app chrome after first-run migration completes.',
            observed: step4Observed,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Opened the app exactly through the user-visible first-run startup path, then observed the migrated hosted session in the chrome.',
          observed:
              'connected=${observation.connectedVisible}; display_name=${observation.displayNameVisible}; login=${observation.loginVisible}; initials=${observation.initialsVisible}',
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
  _prBodyFile.writeAsStringSync(_prBody(result, passed: true));
  _responseFile.writeAsStringSync(_responseSummary(passed: true));
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _responseSummary({required bool passed}) {
  return passed
      ? '# TS-665\n\nReworked the test to drive `TrackStateApp` through first-run startup, moved the SharedPreferences/auth assertions behind a layered testing probe, and verified the migrated hosted session stays visibly connected.\n\nResult: `1 passed, 0 failed`.\n'
      : '# TS-665\n\nReworked the test to use the first-run startup path and layered testing probe, but the product-visible scenario still failed.\n\nResult: `0 passed, 1 failed`.\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final reviewFixes =
      (result['review_fixes'] as List<Object?>?)?.cast<String>() ?? const [];
  final lines = <String>[
    '## TS-665 Rework',
    '',
    '### Review fixes addressed',
    for (final fix in reviewFixes) '- $fix',
    '',
    '### Result',
    passed
        ? '- Passed: first launch migrated the legacy hosted context into one active workspace, re-scoped only the active token, and preserved the visible connected identity.'
        : '- Failed: the first-run app path still does not satisfy the expected hosted migration behavior.',
    '',
    '### Step results',
    ..._markdownStepLines(result),
    '',
    '### Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '### Test file',
    '```text',
    _testFilePath,
    '```',
    '',
    '### How to run',
    '```bash',
    _runCommand,
    '```',
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '### Exact error',
      '```text',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Object?>?) ?? const [];
  return [
    for (final entry in steps.cast<Map<String, Object?>>())
      '- Step ${entry['step']}: **${entry['status']}** — ${entry['action']}\n'
          '  - Observed: ${entry['observed']}',
  ];
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks = (result['human_verification'] as List<Object?>?) ?? const [];
  return [
    for (final entry in checks.cast<Map<String, Object?>>())
      '- ${entry['check']}\n  - Observed: ${entry['observed']}',
  ];
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    'h2. TS-665 First-run hosted workspace migration failed',
    '',
    'h3. Reproduction steps',
    '# Seed SharedPreferences with a legacy hosted token for {code}trackstate/trackstate{code} and an unrelated second legacy repository token.',
    '# Launch the production app through {code}TrackStateApp(){code} with {code}repository{code} unset so startup uses the real first-run migration path.',
    '# Wait for startup to finish and inspect the persisted workspace state, credential scopes, and visible hosted identity.',
    '',
    'h3. Expected result',
    'The app should create exactly one active hosted workspace {code}hosted:trackstate/trackstate@main{code}, mark migration complete, move only the active repository token into workspace scope, keep the unrelated legacy token untouched, and still show the hosted session as connected with {code}Demo User{code} / {code}demo-user{code} / {code}DU{code}.',
    '',
    'h3. Actual result',
    '${result['error'] ?? '<missing>'}',
    '',
    'h3. Missing or broken production capability',
    'The production first-run startup flow did not expose the migrated hosted workspace state and connected hosted identity in the expected observable way when exercised entirely through the public app launch path.',
    '',
    'h3. Failing command',
    '{code:bash}',
    _runCommand,
    '{code}',
    '',
    'h3. Raw output',
    '{noformat}',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '{noformat}',
  ];
  return '${lines.join('\n')}\n';
}
