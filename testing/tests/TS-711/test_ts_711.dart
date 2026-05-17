import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/ts711_workspace_switch_sync_fixture.dart';

const String _ticketKey = 'TS-711';
const String _ticketSummary =
    'Workspace switch disposes the previous sync coordinator and starts the next one immediately';
const String _testFilePath = 'testing/tests/TS-711/test_ts_711.dart';
const String _runCommand =
    'flutter test testing/tests/TS-711/test_ts_711.dart --reporter expanded';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-711 switching workspaces stops the previous background coordinator and starts the new one immediately',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      Ts711WorkspaceSwitchSyncFixture? fixture;
      Ts711WorkspaceSwitchSyncScreen? screen;

      try {
        fixture = await Ts711WorkspaceSwitchSyncFixture.create(tester);
        screen = await fixture.launch();
        await screen.waitForReady(
          Ts711WorkspaceSwitchSyncFixture.workspaceADisplayName,
        );
        await screen.openBoardSection();

        result['workspace_a_repository_path'] =
            fixture.workspaceARepositoryPath;
        result['workspace_b_repository_path'] =
            fixture.workspaceBRepositoryPath;
        result['workspace_a_id'] = fixture.workspaceA.id;
        result['workspace_b_id'] = fixture.workspaceB.id;

        final failures = <String>[];

        final workspaceStateBeforeSwitch = await fixture.loadWorkspaceState();
        result['active_workspace_before_switch'] =
            workspaceStateBeforeSwitch.activeWorkspaceId;
        result['workspace_a_sync_calls_before_switch'] = fixture
            .workspaceARepository
            .syncCalls
            .map((call) => call.toJson())
            .toList(growable: false);

        final initialWorkspaceASyncCount =
            fixture.workspaceARepository.syncCallCount;
        final initialWorkspaceBSyncCount =
            fixture.workspaceBRepository.syncCallCount;

        if (!screen.isWorkspaceSwitcherTriggerVisible ||
            !screen.triggerContainsText(
              Ts711WorkspaceSwitchSyncFixture.workspaceADisplayName,
            ) ||
            !screen.isBoardVisible ||
            workspaceStateBeforeSwitch.activeWorkspaceId !=
                fixture.workspaceA.id ||
            initialWorkspaceASyncCount != 1 ||
            initialWorkspaceBSyncCount != 0) {
          final observed =
              'trigger_visible=${screen.isWorkspaceSwitcherTriggerVisible}; '
              'trigger_text_matches=${screen.triggerContainsText(Ts711WorkspaceSwitchSyncFixture.workspaceADisplayName)}; '
              'board_visible=${screen.isBoardVisible}; '
              'active_workspace=${workspaceStateBeforeSwitch.activeWorkspaceId}; '
              'workspace_a_sync_count=$initialWorkspaceASyncCount; '
              'workspace_b_sync_count=$initialWorkspaceBSyncCount';
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Launch the app with Workspace-A active and background sync already started.',
            observed: observed,
          );
          failures.add(
            'Step 1 failed: Workspace-A was not the visible active workspace with exactly one initial background sync check before opening the switcher.\n'
            'Observed: $observed\n'
            'Visible texts: ${_formatList(screen.visibleTexts())}\n'
            'Visible semantics: ${_formatList(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action:
                'Launch the app with Workspace-A active and background sync already started.',
            observed:
                'trigger=${Ts711WorkspaceSwitchSyncFixture.workspaceADisplayName}; board_visible=true; active_workspace=${workspaceStateBeforeSwitch.activeWorkspaceId}; workspace_a_sync_count=$initialWorkspaceASyncCount; workspace_b_sync_count=$initialWorkspaceBSyncCount',
          );
        }

        final switchRequestedAt = DateTime.now().toUtc();
        await screen.openWorkspaceSwitcher();
        if (!screen.canOpenWorkspace(fixture.workspaceB.id)) {
          final observed =
              'workspace_b_open_visible=false; visible_texts=${_formatList(screen.visibleTexts())}';
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: 'Open the workspace switcher and select Workspace-B.',
            observed: observed,
          );
          failures.add(
            'Step 2 failed: the workspace switcher did not expose an Open action for Workspace-B.\n'
            'Observed: $observed',
          );
        } else {
          await screen.openWorkspace(fixture.workspaceB.id);
          await screen.waitForWorkspaceSwitch(
            Ts711WorkspaceSwitchSyncFixture.workspaceBDisplayName,
          );
          final workspaceStateAfterSwitch = await fixture.loadWorkspaceState();
          result['active_workspace_after_switch'] =
              workspaceStateAfterSwitch.activeWorkspaceId;
          result['open_requests_after_switch'] = List<String>.from(
            fixture.localOpenRequests,
          );
          result['workspace_b_sync_calls_after_switch'] = fixture
              .workspaceBRepository
              .syncCalls
              .map((call) => call.toJson())
              .toList(growable: false);

          final workspaceBImmediateCall =
              fixture.workspaceBRepository.syncCalls.isEmpty
              ? null
              : fixture.workspaceBRepository.syncCalls.first;
          final immediateObserved =
              'trigger_matches_workspace_b=${screen.triggerContainsText(Ts711WorkspaceSwitchSyncFixture.workspaceBDisplayName)}; '
              'active_workspace=${workspaceStateAfterSwitch.activeWorkspaceId}; '
              'open_requests=${_formatList(fixture.localOpenRequests)}; '
              'workspace_b_sync_count=${fixture.workspaceBRepository.syncCallCount}; '
              'workspace_b_first_previous_revision=${workspaceBImmediateCall?.previousRepositoryRevision ?? 'null'}; '
              'workspace_b_first_checked_at=${workspaceBImmediateCall?.checkedAt.toIso8601String() ?? 'missing'}; '
              'switch_requested_at=${switchRequestedAt.toIso8601String()}';

          if (!screen.triggerContainsText(
                Ts711WorkspaceSwitchSyncFixture.workspaceBDisplayName,
              ) ||
              workspaceStateAfterSwitch.activeWorkspaceId !=
                  fixture.workspaceB.id ||
              fixture.localOpenRequests.length < 2 ||
              fixture.localOpenRequests.first !=
                  fixture.workspaceARepositoryPath ||
              fixture.localOpenRequests[1] !=
                  fixture.workspaceBRepositoryPath ||
              fixture.workspaceBRepository.syncCallCount != 1 ||
              workspaceBImmediateCall == null ||
              workspaceBImmediateCall.previousRepositoryRevision != null ||
              workspaceBImmediateCall.previousSessionRevision != null) {
            _recordStep(
              result,
              step: 2,
              status: 'failed',
              action: 'Open the workspace switcher and select Workspace-B.',
              observed: immediateObserved,
            );
            failures.add(
              'Step 2 failed: selecting Workspace-B did not visibly activate Workspace-B and start a brand-new immediate sync coordinator.\n'
              'Observed: $immediateObserved',
            );
          } else {
            _recordStep(
              result,
              step: 2,
              status: 'passed',
              action: 'Open the workspace switcher and select Workspace-B.',
              observed: immediateObserved,
            );
          }
        }

        final workspaceASyncCountAfterSwitch =
            fixture.workspaceARepository.syncCallCount;
        await tester.pump(const Duration(seconds: 61));
        await tester.pumpAndSettle();

        final workspaceAAfterCadence = fixture.workspaceARepository.syncCalls;
        final workspaceBAfterCadence = fixture.workspaceBRepository.syncCalls;
        result['workspace_a_sync_calls_after_cadence'] = workspaceAAfterCadence
            .map((call) => call.toJson())
            .toList(growable: false);
        result['workspace_b_sync_calls_after_cadence'] = workspaceBAfterCadence
            .map((call) => call.toJson())
            .toList(growable: false);

        final cadenceObserved =
            'workspace_a_sync_count_before_cadence=$workspaceASyncCountAfterSwitch; '
            'workspace_a_sync_count_after_cadence=${workspaceAAfterCadence.length}; '
            'workspace_b_sync_count_after_cadence=${workspaceBAfterCadence.length}; '
            'workspace_b_first_previous_revision=${workspaceBAfterCadence.first.previousRepositoryRevision ?? 'null'}';

        if (workspaceAAfterCadence.length != workspaceASyncCountAfterSwitch ||
            workspaceBAfterCadence.isEmpty) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Observe the sync logs after the switch and wait longer than the 60-second cadence.',
            observed: cadenceObserved,
          );
          failures.add(
            'Step 3 failed: Workspace-A did not stay disposed after waiting longer than the old 60-second cadence timer.\n'
            'Observed: $cadenceObserved',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Observe the sync logs after the switch and wait longer than the 60-second cadence.',
            observed: cadenceObserved,
          );
        }

        await screen.openWorkspaceSwitcher();
        final humanObserved =
            'trigger=${Ts711WorkspaceSwitchSyncFixture.workspaceBDisplayName}; '
            'board_visible=${screen.isBoardVisible}; '
            'workspace_b_active=${screen.workspaceRowContainsText(fixture.workspaceB.id, 'Active')}; '
            'workspace_a_open_available=${screen.canOpenWorkspace(fixture.workspaceA.id)}; '
            'visible_texts=${_formatList(screen.visibleTexts())}';
        _recordHumanVerification(
          result,
          check:
              'Verified the visible active workspace summary and board surface from a user perspective after switching to Workspace-B.',
          observed: humanObserved,
        );
        if (!screen.triggerContainsText(
              Ts711WorkspaceSwitchSyncFixture.workspaceBDisplayName,
            ) ||
            !screen.isBoardVisible ||
            !screen.workspaceRowContainsText(fixture.workspaceB.id, 'Active') ||
            !screen.canOpenWorkspace(fixture.workspaceA.id)) {
          failures.add(
            'Human-style verification failed: the UI did not keep Workspace-B visibly active with the board still rendered while Workspace-A became the inactive reopenable option.\n'
            'Observed: $humanObserved',
          );
        }

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        screen?.dispose();
        await fixture?.dispose();
        semantics.dispose();
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
    '* Seeded two valid local workspaces and launched the production workspace switcher with Workspace-A active.',
    '* Selected Workspace-B through the real UI and recorded the production workspace sync repository check log for both workspaces.',
    '* Verified Workspace-B performed its first sync before any 60-second cadence wait elapsed.',
    '* Waited longer than 60 seconds in the widget test clock and confirmed Workspace-A never performed another sync check after disposal.',
    '',
    'h4. Human-style verification',
    '* Confirmed the visible workspace switcher trigger changed from Workspace-A to Workspace-B.',
    '* Confirmed the Board surface stayed visible after the switch and that reopening the switcher marked Workspace-B as Active.',
    '* Confirmed Workspace-A became the inactive workspace that could be reopened.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: switching to Workspace-B stopped Workspace-A after its initial sync, started a brand-new immediate sync for Workspace-B, and the disposed Workspace-A 60-second timer never fired again.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Workspace-A repository path: {noformat}${result['workspace_a_repository_path'] ?? '<missing>'}{noformat}',
    '* Workspace-B repository path: {noformat}${result['workspace_b_repository_path'] ?? '<missing>'}{noformat}',
    '',
    'h4. Step results',
    ..._jiraStepLines(result),
    '',
    'h4. Human-style verification details',
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
    '- Seeded two valid local workspaces and launched the production workspace switcher with Workspace-A active.',
    '- Selected Workspace-B through the real UI and recorded the production workspace sync repository check log for both workspaces.',
    '- Verified Workspace-B performed an immediate first sync before any 60-second cadence wait elapsed.',
    '- Advanced widget-test time past 60 seconds and confirmed Workspace-A never performed another sync check after disposal.',
    '',
    '## Human-style verification',
    '- Confirmed the visible workspace switcher trigger changed from Workspace-A to Workspace-B.',
    '- Confirmed the Board surface stayed visible after the switch and that reopening the switcher marked Workspace-B as `Active`.',
    '- Confirmed Workspace-A became the inactive workspace that could be reopened.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: switching to Workspace-B stopped Workspace-A after its initial sync, started a brand-new immediate sync for Workspace-B, and the disposed Workspace-A 60-second timer never fired again.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification details',
    ..._markdownHumanVerificationLines(result),
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
          ? 'Passed: switching to Workspace-B stopped Workspace-A after its initial sync, started Workspace-B immediately, and Workspace-A never synced again after its old 60-second timer window passed.'
          : 'Failed: switching workspaces did not stop the previous sync coordinator and start the new one exactly as expected.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln(
      'Workspace-A repository path: `${result['workspace_a_repository_path'] ?? '<missing>'}`',
    )
    ..writeln(
      'Workspace-B repository path: `${result['workspace_b_repository_path'] ?? '<missing>'}`',
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
    'Switching workspaces does not fully dispose the previous background sync coordinator or does not start the new workspace coordinator immediately.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** when Workspace-B is selected from the workspace switcher, Workspace-A stops after its existing sync activity, its 60-second timer does not fire again, and Workspace-B starts a brand-new immediate sync without waiting for the cadence.',
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
    '- Workspace-A repository path: `${result['workspace_a_repository_path'] ?? '<missing>'}`',
    '- Workspace-B repository path: `${result['workspace_b_repository_path'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Active workspace before switch: ${result['active_workspace_before_switch'] ?? '<missing>'}',
    'Active workspace after switch: ${result['active_workspace_after_switch'] ?? '<missing>'}',
    'Open requests after switch: ${result['open_requests_after_switch'] ?? '<missing>'}',
    'Workspace-A sync calls before switch: ${result['workspace_a_sync_calls_before_switch'] ?? '<missing>'}',
    'Workspace-B sync calls after switch: ${result['workspace_b_sync_calls_after_switch'] ?? '<missing>'}',
    'Workspace-A sync calls after cadence: ${result['workspace_a_sync_calls_after_cadence'] ?? '<missing>'}',
    'Workspace-B sync calls after cadence: ${result['workspace_b_sync_calls_after_cadence'] ?? '<missing>'}',
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
  if (checks.isEmpty) {
    return const ['* No additional human-style checks were recorded.'];
  }
  return [
    for (final check in checks)
      '* ${check['check']}\n  Observed: {noformat}${check['observed']}{noformat}',
  ];
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const ['- No additional human-style checks were recorded.'];
  }
  return [
    for (final check in checks)
      '- ${check['check']}\n  - Observed: `${check['observed']}`',
  ];
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '${step['status'] == 'passed' ? '1. ✅' : '1. ❌'} ${step['action']}\n'
          '   - Observed: `${step['observed']}`',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  final failedSteps =
      ((result['steps'] as List<Map<String, Object?>>?) ?? const [])
          .where((step) => step['status'] != 'passed')
          .toList(growable: false);
  if (failedSteps.isEmpty) {
    return 'The scenario failed unexpectedly without a recorded step result.';
  }
  final step = failedSteps.first;
  return 'Step ${step['step']} did not match the expectation. Observed `${step['observed']}`.';
}

String _formatList(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
