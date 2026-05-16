import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/repositories/ts734_refresh_matrix_repository.dart';

const String _ticketKey = 'TS-774';
const String _ticketSummary =
    'Project metadata sync — global snapshot reload counter remains unchanged';
const String _testFilePath = 'testing/tests/TS-774/test_ts_774.dart';
const String _runCommand =
    'flutter test testing/tests/TS-774/test_ts_774.dart --reporter expanded';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-774 projectMeta-only sync refreshes metadata without a global snapshot reload',
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
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts734RefreshMatrixRepository();

      try {
        await repository.connectForTest();
        await screen.pump(repository);

        result['repository'] = 'trackstate/trackstate';
        result['initial_release_tag_prefix'] =
            Ts734RefreshMatrixRepository.initialTagPrefix;
        result['updated_release_tag_prefix'] =
            Ts734RefreshMatrixRepository.updatedTagPrefix;

        final failures = <String>[];
        final baselineLoadSnapshotCount = repository.loadSnapshotCalls;

        await screen.openSection('Dashboard');
        final dashboardSemanticsBeforeSync = screen
            .visibleSemanticsLabelsSnapshot();
        final dashboardVisibleBeforeSync = _snapshotContains(
          dashboardSemanticsBeforeSync,
          'Open Issues',
        );

        await screen.openSection('Settings');
        await screen.expectTextVisible('Project Settings');
        final attachmentsTabOpenedBeforeSync = await screen.tapVisibleControl(
          'Attachments',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 200));
        final initialReleaseTagPrefix = await screen.readLabeledTextFieldValue(
          'Release tag prefix',
        );
        final monitoringObserved =
            'dashboard_visible=$dashboardVisibleBeforeSync; '
            'attachments_tab_opened=$attachmentsTabOpenedBeforeSync; '
            'baseline_load_snapshot_count=$baselineLoadSnapshotCount; '
            'initial_release_tag_prefix=${initialReleaseTagPrefix ?? '<missing>'}; '
            'dashboard_semantics=${_formatSnapshot(dashboardSemanticsBeforeSync)}';
        if (!dashboardVisibleBeforeSync ||
            !attachmentsTabOpenedBeforeSync ||
            initialReleaseTagPrefix !=
                Ts734RefreshMatrixRepository.initialTagPrefix) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action:
                'Initialize load_snapshot_delta monitoring and confirm the pre-sync Dashboard and Settings Attachments state.',
            observed: monitoringObserved,
          );
          failures.add(
            'Step 1 failed: the app did not expose the expected pre-sync Dashboard/Settings state before the projectMeta-only refresh.\n'
            'Observed: $monitoringObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action:
                'Initialize load_snapshot_delta monitoring and confirm the pre-sync Dashboard and Settings Attachments state.',
            observed: monitoringObserved,
          );
        }

        await repository.emitProjectMetaOnlyRefresh();
        await _resumeApp(tester);

        await screen.openSection('Dashboard');
        final dashboardSemanticsAfterSync = screen
            .visibleSemanticsLabelsSnapshot();
        final openIssuesVisible = _snapshotContains(
          dashboardSemanticsAfterSync,
          'Open Issues 3',
        );
        final inProgressVisible = _snapshotContains(
          dashboardSemanticsAfterSync,
          'Issues in Progress 1',
        );
        final completedVisible = _snapshotContains(
          dashboardSemanticsAfterSync,
          'Completed 0',
        );
        final dashboardObserved =
            'open_issues_3=$openIssuesVisible; '
            'issues_in_progress_1=$inProgressVisible; '
            'completed_0=$completedVisible; '
            'dashboard_semantics=${_formatSnapshot(dashboardSemanticsAfterSync)}';
        if (!openIssuesVisible || !inProgressVisible || !completedVisible) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Simulate a projectMeta-only background sync event and confirm the visible Dashboard counters stay readable for the unchanged issue data.',
            observed: dashboardObserved,
          );
          failures.add(
            'Step 2 failed: the Dashboard counters did not remain readable on the visible Dashboard surface after the projectMeta-only sync.\n'
            'Observed: $dashboardObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action:
                'Simulate a projectMeta-only background sync event and confirm the visible Dashboard counters stay readable for the unchanged issue data.',
            observed: dashboardObserved,
          );
        }

        await screen.openSection('Settings');
        await screen.expectTextVisible('Project Settings');
        final attachmentsTabOpenedAfterSync = await screen.tapVisibleControl(
          'Attachments',
        );
        await screen.waitWithoutInteraction(const Duration(milliseconds: 200));
        final updatedReleaseTagPrefix = await screen.readLabeledTextFieldValue(
          'Release tag prefix',
        );
        result['observed_release_tag_prefix'] = updatedReleaseTagPrefix;
        final settingsObserved =
            'attachments_tab_opened=$attachmentsTabOpenedAfterSync; '
            'release_tag_prefix=${updatedReleaseTagPrefix ?? '<missing>'}; '
            'settings_texts=${_formatSnapshot(screen.visibleTextsSnapshot())}';
        if (!attachmentsTabOpenedAfterSync ||
            updatedReleaseTagPrefix !=
                Ts734RefreshMatrixRepository.updatedTagPrefix) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action:
                'Observe the Settings Attachments display after the projectMeta-only sync.',
            observed: settingsObserved,
          );
          failures.add(
            'Step 3 failed: the Settings Attachments display did not show the updated release tag prefix after the projectMeta-only sync.\n'
            'Observed: $settingsObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action:
                'Observe the Settings Attachments display after the projectMeta-only sync.',
            observed: settingsObserved,
          );
        }

        final loadSnapshotDelta =
            repository.loadSnapshotCalls - baselineLoadSnapshotCount;
        result['load_snapshot_delta'] = loadSnapshotDelta;
        final counterObserved =
            'baseline_load_snapshot_count=$baselineLoadSnapshotCount; '
            'final_load_snapshot_count=${repository.loadSnapshotCalls}; '
            'load_snapshot_delta=$loadSnapshotDelta';
        if (loadSnapshotDelta != 0) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action:
                'Inspect load_snapshot_delta after the projectMeta-only UI updates complete.',
            observed: counterObserved,
          );
          failures.add(
            'Step 4 failed: the projectMeta-only sync triggered a global snapshot reload.\n'
            'Observed: $counterObserved',
          );
        } else {
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action:
                'Inspect load_snapshot_delta after the projectMeta-only UI updates complete.',
            observed: counterObserved,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the Dashboard after the projectMeta-only sync exactly as a user would and confirmed the visible counter labels remained readable for the unchanged issue data.',
          observed:
              'dashboard_semantics=${_formatSnapshot(dashboardSemanticsAfterSync)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Opened Settings > Attachments and confirmed the Release tag prefix field visibly changed from the original value to the refreshed value.',
          observed:
              'initial_release_tag_prefix=${initialReleaseTagPrefix ?? '<missing>'}; '
              'updated_release_tag_prefix=${updatedReleaseTagPrefix ?? '<missing>'}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the metadata refresh behaved as a granular update by checking the monitored load_snapshot_delta counter after the UI finished updating.',
          observed: counterObserved,
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
      } finally {
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 45)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

Future<void> _resumeApp(WidgetTester tester) async {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.pumpAndSettle();
}

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
    '* Launched the production TrackState widget app with the mutable hosted repository fixture used by the existing sync-matrix regression coverage.',
    '* Monitored the hosted snapshot reload counter before and after a simulated {{projectMeta-only}} background sync event.',
    '* Verified the visible Dashboard counter surface remained readable while the projectMeta-only sync refreshed the Settings -> Attachments release tag prefix.',
    '* Confirmed the projectMeta-only sync stayed granular by leaving {{load_snapshot_delta}} at 0 after the UI refreshed.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the {{projectMeta-only}} sync refreshed the Settings Attachments metadata, preserved the visible Dashboard counter surface, and did not trigger a global snapshot reload.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository: {noformat}${result['repository'] ?? '<missing>'}{noformat}',
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
    '- Launched the production TrackState widget app with the mutable hosted repository fixture already used for refresh-matrix regressions.',
    '- Captured the baseline snapshot reload counter, then simulated a `projectMeta`-only background sync event.',
    '- Verified the visible Dashboard counter surface stayed readable with the unchanged baseline values `Open Issues 3`, `Issues in Progress 1`, and `Completed 0`.',
    '- Verified `Settings > Attachments` showed the refreshed `Release tag prefix` and confirmed `load_snapshot_delta` stayed at `0`.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: the `projectMeta`-only sync refreshed the visible Settings metadata, preserved the Dashboard counter surface, and avoided a global snapshot reload.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
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
          ? 'Passed: the projectMeta-only sync refreshed the Settings release tag prefix, preserved the visible Dashboard counters, and kept the monitored snapshot reload counter unchanged.'
          : 'Failed: the projectMeta-only sync did not preserve the expected granular-refresh behavior.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Observed release tag prefix: `${result['observed_release_tag_prefix'] ?? '<missing>'}`',
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
    _bugSummary(result),
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** a `projectMeta`-only background sync keeps the visible Dashboard counter surface readable for unchanged issue data, refreshes the Settings > Attachments release tag prefix, and does not increment `load_snapshot_delta`.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    _missingCapabilityLine(result),
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
    'Observed release tag prefix: ${result['observed_release_tag_prefix'] ?? '<missing>'}',
    'Observed load_snapshot_delta: ${result['load_snapshot_delta'] ?? '<missing>'}',
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
  if (steps.isEmpty) {
    return const ['1. No step results were recorded before the failure.'];
  }
  return [
    for (final step in steps)
      '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
          '   - Observed: ${step['observed']}',
  ];
}

List<String> _bugLogLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>['<no step logs recorded>'];
  }
  return [
    for (final step in steps)
      'Step ${step['step']} (${step['status']}): ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result) ?? <String, Object?>{};
  if (failedStep.isEmpty) {
    return 'The test failed before recording a detailed step observation.';
  }
  return 'Step ${failedStep['step']} failed with the observation `${failedStep['observed']}`.';
}

String _bugSummary(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  if (failedStep?['step'] == 2) {
    return 'A `projectMeta`-only hosted workspace sync does not preserve a readable Dashboard counter surface after the metadata update.';
  }
  if (failedStep?['step'] == 3) {
    return 'A `projectMeta`-only hosted workspace sync does not refresh the Settings > Attachments release tag prefix after the metadata update.';
  }
  if (failedStep?['step'] == 4) {
    return 'A `projectMeta`-only hosted workspace sync still triggers a global snapshot reload instead of remaining a granular metadata update.';
  }
  return 'The hosted `projectMeta`-only refresh path does not deliver the expected granular metadata update behavior.';
}

String _missingCapabilityLine(Map<String, Object?> result) {
  final failedStep = _firstFailedStep(result);
  if (failedStep?['step'] == 2 || failedStep?['step'] == 3) {
    return '- The production-visible workspace sync path for `projectMeta`-only changes does not keep the visible dashboard/settings surfaces coherent while applying refreshed project metadata.';
  }
  if (failedStep?['step'] == 4) {
    return '- The production-visible workspace sync path for `projectMeta`-only changes still falls back to a full snapshot reload instead of handling metadata changes as a scoped update.';
  }
  return '- The production-visible `projectMeta`-only refresh path does not preserve the granular update behavior required by the ticket.';
}

Map<String, Object?>? _firstFailedStep(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  for (final step in steps) {
    if (step['status'] != 'passed') {
      return step;
    }
  }
  return null;
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
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

bool _snapshotContains(List<String> snapshot, String expected) {
  for (final value in snapshot) {
    final trimmed = value.trim();
    if (trimmed == expected || trimmed.contains(expected)) {
      return true;
    }
  }
  return false;
}
