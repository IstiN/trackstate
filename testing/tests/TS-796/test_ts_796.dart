import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../../fixtures/local_hosted_workspace_fixture.dart';

const String _ticketKey = 'TS-796';
const String _ticketSummary =
    'Local repository label mapping - sign-in controls are not suppressed by metadata';
const String _runCommand =
    'flutter test testing/tests/TS-796/test_ts_796.dart --reporter expanded';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-796 preserves Connect GitHub while active local metadata is visible',
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
      final TrackStateAppComponent app = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      LocalHostedWorkspaceFixture? fixture;

      try {
        fixture = await LocalHostedWorkspaceFixture.create();
        await app.pumpWorkspaceProfileApp(
          workspaceProfileService: fixture.workspaceProfileService,
          openLocalRepository: fixture.openLocalRepository,
        );

        result['active_local_workspace_id'] = fixture.activeLocalWorkspace.id;
        result['inactive_hosted_workspace_id'] =
            fixture.inactiveHostedWorkspace.id;
        result['active_local_repository_path'] =
            fixture.activeLocalRepositoryPath;

        final failures = <String>[];

        await app.openWorkspaceSwitcher();
        result['visible_texts_in_switcher'] = app.visibleTextsSnapshot();
        result['visible_semantics_in_switcher'] = app
            .visibleSemanticsLabelsSnapshot();

        final workspaceSwitcherVisible = await app.isWorkspaceSwitcherVisible();

        final step1Observed =
            'switcher_visible=$workspaceSwitcherVisible; '
            'active_workspace_id=${fixture.activeLocalWorkspace.id}; '
            'visible_texts=${_formatList(app.visibleTextsSnapshot())}';
        _recordStep(
          result,
          step: 1,
          status: workspaceSwitcherVisible ? 'passed' : 'failed',
          action: 'Open the workspace switcher.',
          observed: step1Observed,
        );
        if (!workspaceSwitcherVisible) {
          failures.add(
            'Step 1 failed: the workspace switcher did not open from the active local workspace.\n'
            'Observed: $step1Observed',
          );
        }

        final activeLocalRowHasDisplayName = await app.workspaceRowContainsText(
          fixture.activeLocalWorkspace.id,
          LocalHostedWorkspaceFixture.activeLocalDisplayName,
        );
        final activeLocalRowHasPath = await app
            .workspaceRowContainsTextContaining(
              fixture.activeLocalWorkspace.id,
              fixture.activeLocalRepositoryPath,
            );
        final activeLocalRowHasBranch = await app
            .workspaceRowContainsTextContaining(
              fixture.activeLocalWorkspace.id,
              'Branch: main',
            );
        final activeLocalRowHasLocalBadge = await app.workspaceRowContainsText(
          fixture.activeLocalWorkspace.id,
          'Local',
        );
        final activeLocalRowHasLocalGitBadge = await app
            .workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Local Git',
            );
        final activeLocalRowHasActiveLabel = await app.workspaceRowContainsText(
          fixture.activeLocalWorkspace.id,
          'Active',
        );
        final step2Observed =
            'display_name_visible=$activeLocalRowHasDisplayName; '
            'repository_path_visible=$activeLocalRowHasPath; '
            'branch_visible=$activeLocalRowHasBranch; '
            'local_badge_visible=$activeLocalRowHasLocalBadge; '
            'local_git_badge_visible=$activeLocalRowHasLocalGitBadge; '
            'active_label_visible=$activeLocalRowHasActiveLabel';
        final step2Passed =
            activeLocalRowHasDisplayName &&
            activeLocalRowHasPath &&
            activeLocalRowHasBranch &&
            activeLocalRowHasLocalBadge &&
            activeLocalRowHasLocalGitBadge &&
            activeLocalRowHasActiveLabel;
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action:
              'Inspect the active local workspace row for repository labels and metadata.',
          observed: step2Observed,
        );
        if (!step2Passed) {
          failures.add(
            'Step 2 failed: the active local workspace row did not keep the expected local repository metadata visible.\n'
            'Observed: $step2Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the active local row in Workspace switcher as a user would and checked its visible name, path, branch, and state badges.',
          observed:
              'active_row=${LocalHostedWorkspaceFixture.activeLocalDisplayName}; '
              'path=${fixture.activeLocalRepositoryPath}; '
              'branch=main; '
              'visible_texts=${_formatList(app.visibleTextsSnapshot())}',
        );

        await app.closeWorkspaceSwitcher();
        await app.openSection('Settings');

        final repositoryAccessVisible =
            await app.isTextVisible('Repository access') ||
            await app.isSemanticsLabelVisible('Repository access');
        final localGitRuntimeVisible =
            await app.isTextVisible('Local Git runtime') ||
            await app.isSemanticsLabelVisible('Local Git runtime');
        final connectGitHubVisible =
            await app.isTextVisible('Connect GitHub') ||
            await app.isSemanticsLabelVisible('Connect GitHub');
        final repositoryPathFieldVisible = await app.isTextFieldVisible(
          'Repository Path',
        );
        final writeBranchFieldVisible = await app.isTextFieldVisible(
          'Write Branch',
        );
        final repositoryPathValue = await app.readLabeledTextFieldValue(
          'Repository Path',
        );
        final writeBranchValue = await app.readLabeledTextFieldValue(
          'Write Branch',
        );
        result['visible_texts_in_settings'] = app.visibleTextsSnapshot();
        result['visible_semantics_in_settings'] = app
            .visibleSemanticsLabelsSnapshot();
        result['repository_path_value_in_settings'] = repositoryPathValue;
        result['write_branch_value_in_settings'] = writeBranchValue;

        final step3Observed =
            'repository_access_visible=$repositoryAccessVisible; '
            'local_git_runtime_visible=$localGitRuntimeVisible; '
            'connect_github_visible=$connectGitHubVisible; '
            'repository_path_field_visible=$repositoryPathFieldVisible; '
            'write_branch_field_visible=$writeBranchFieldVisible; '
            'repository_path_value=${repositoryPathValue ?? '<missing>'}; '
            'write_branch_value=${writeBranchValue ?? '<missing>'}; '
            'visible_texts=${_formatList(app.visibleTextsSnapshot())}';
        final step3Passed =
            repositoryAccessVisible &&
            localGitRuntimeVisible &&
            connectGitHubVisible &&
            repositoryPathFieldVisible &&
            writeBranchFieldVisible &&
            repositoryPathValue == fixture.activeLocalRepositoryPath &&
            writeBranchValue == 'main';
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action:
              'Inspect the active local repository-access surface for local metadata and the Connect GitHub control.',
          observed: step3Observed,
        );
        if (!step3Passed) {
          failures.add(
            'Step 3 failed: the active local repository-access surface did not keep the expected local metadata and Connect GitHub control visible together.\n'
            'Observed: $step3Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the Settings > Repository access area from the active local workspace and checked that the Connect GitHub control was visible beside the local Repository Path and Write Branch fields.',
          observed:
              'connect_github_visible=$connectGitHubVisible; '
              'repository_path_value=${repositoryPathValue ?? '<missing>'}; '
              'write_branch_value=${writeBranchValue ?? '<missing>'}',
        );

        var tappedConnectGitHub = false;
        var connectDialogVisible = false;
        var fineGrainedTokenVisible = false;
        var connectTokenVisible = false;
        var cancelVisible = false;
        var cancelledDialog = false;
        var repositoryPathFieldStillVisibleAfterCancel = false;
        var writeBranchFieldStillVisibleAfterCancel = false;

        if (connectGitHubVisible) {
          tappedConnectGitHub = await app.tapVisibleControl('Connect GitHub');
          connectDialogVisible =
              await app.isDialogTextVisible('Connect GitHub') ||
              await app.isTextFieldVisible('Fine-grained token') ||
              await app.isDialogTextVisible('Connect token');
          fineGrainedTokenVisible = await app.isTextFieldVisible(
            'Fine-grained token',
          );
          connectTokenVisible = await app.isDialogTextVisible('Connect token');
          cancelVisible = await app.isDialogTextVisible('Cancel');
          if (cancelVisible) {
            cancelledDialog = await app.tapDialogControl('Cancel');
          }
          repositoryPathFieldStillVisibleAfterCancel = await app
              .isTextFieldVisible('Repository Path');
          writeBranchFieldStillVisibleAfterCancel = await app
              .isTextFieldVisible('Write Branch');
        }

        result['visible_texts_after_connect_attempt'] = app
            .visibleTextsSnapshot();
        result['visible_semantics_after_connect_attempt'] = app
            .visibleSemanticsLabelsSnapshot();

        final step4Observed =
            'tapped_connect_github=$tappedConnectGitHub; '
            'connect_dialog_visible=$connectDialogVisible; '
            'fine_grained_token_visible=$fineGrainedTokenVisible; '
            'connect_token_visible=$connectTokenVisible; '
            'cancel_visible=$cancelVisible; '
            'cancelled_dialog=$cancelledDialog; '
            'repository_path_still_visible_after_cancel=$repositoryPathFieldStillVisibleAfterCancel; '
            'write_branch_still_visible_after_cancel=$writeBranchFieldStillVisibleAfterCancel; '
            'visible_texts=${_formatList(app.visibleTextsSnapshot())}';
        final step4Passed =
            connectGitHubVisible &&
            tappedConnectGitHub &&
            connectDialogVisible &&
            fineGrainedTokenVisible &&
            connectTokenVisible &&
            cancelVisible &&
            cancelledDialog &&
            repositoryPathFieldStillVisibleAfterCancel &&
            writeBranchFieldStillVisibleAfterCancel;
        _recordStep(
          result,
          step: 4,
          status: step4Passed ? 'passed' : 'failed',
          action:
              'Open the Connect GitHub flow from the active local workspace and return to the local configuration.',
          observed: step4Observed,
        );
        if (!step4Passed) {
          failures.add(
            'Step 4 failed: the active local Connect GitHub control was not usable without losing the visible local metadata.\n'
            'Observed: $step4Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Tapped the visible Connect GitHub action, confirmed the token dialog opened, then closed it and confirmed the user returned to the same local Repository access form.',
          observed:
              'dialog_opened=$connectDialogVisible; '
              'fine_grained_token_visible=$fineGrainedTokenVisible; '
              'returned_to_local_fields=${repositoryPathFieldStillVisibleAfterCancel && writeBranchFieldStillVisibleAfterCancel}',
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
        app.resetView();
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
    _bugDescriptionFile.deleteSync(recursive: false);
  }
  _resultFile.writeAsStringSync(
    jsonEncode(<String, Object?>{
          'status': 'passed',
          'passed': 1,
          'failed': 0,
          'skipped': 0,
          'summary': '1 passed, 0 failed',
        }) +
        '\n',
  );
  final summary = _markdownSummary(result, passed: true);
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: true));
  _prBodyFile.writeAsStringSync(summary);
  _responseFile.writeAsStringSync(summary);
}

void _writeFailureOutputs(Map<String, Object?> result) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: $_ticketKey failed'}';
  _resultFile.writeAsStringSync(
    jsonEncode(<String, Object?>{
          'status': 'failed',
          'passed': 0,
          'failed': 1,
          'skipped': 0,
          'summary': '0 passed, 1 failed',
          'error': error,
        }) +
        '\n',
  );
  final summary = _markdownSummary(result, passed: false);
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(summary);
  _responseFile.writeAsStringSync(summary);
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _jiraComment(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $status',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was automated',
    '* Seeded one active local workspace and one inactive hosted workspace in the production workspace store.',
    '* Opened *Workspace switcher* and verified the active local row kept the visible repository path, branch metadata, and {{Local Git}} state.',
    '* Opened *Settings* from that same active local workspace and verified the visible {{Connect GitHub}} control remained available next to the local {{Repository Path}} and {{Write Branch}} fields.',
    '* Activated {{Connect GitHub}} and verified the production token dialog opened, then closed it and confirmed the local metadata stayed visible.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result.'
        : '* Did not match the expected result. ${_jiraEscape(_failedStep(result))}',
    '* Environment: {{flutter test}}, OS {{{${result['os']}}}}.',
    '',
    'h4. Step results',
    ..._stepLines(result, jira: true),
    '',
    'h4. Human-style verification',
    ..._humanVerificationLines(result, jira: true),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      'h4. Exact error',
      '{code}',
      '${result['traceback'] ?? result['error'] ?? ''}',
      '{code}',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _markdownSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $status',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '## What was automated',
    '- Seeded one active local workspace and one inactive hosted workspace in the production workspace store.',
    '- Opened **Workspace switcher** and verified the active local row kept the visible repository path, branch metadata, and `Local Git` state.',
    '- Opened **Settings** from that same active local workspace and verified the visible `Connect GitHub` control remained available next to the local `Repository Path` and `Write Branch` fields.',
    '- Activated `Connect GitHub` and verified the production token dialog opened, then closed it and confirmed the local metadata stayed visible.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result.'
        : '- Did not match the expected result. ${_failedStep(result)}',
    '- Run command: `$_runCommand`',
    '',
    '## Step results',
    ..._stepLines(result, jira: false),
    '',
    '## Human-style verification',
    ..._humanVerificationLines(result, jira: false),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```text',
      '${result['traceback'] ?? result['error'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  return [
    '# $_ticketKey - Active local repository metadata suppresses or breaks the GitHub sign-in control',
    '',
    '## Reproduction steps',
    ..._bugReproductionLines(result),
    '',
    '## Expected result',
    "The active local workspace should keep its local repository metadata/path visible while also exposing a visible, usable `Connect GitHub` control for the same workspace state.",
    '',
    '## Actual result',
    _actualResult(result),
    '',
    '## Environment details',
    '- URL/runtime: `flutter test` widget runtime',
    '- OS: `${result['os'] ?? 'unknown'}`',
    '- Active local repository path: `${result['active_local_repository_path'] ?? '<unknown>'}`',
    '- Command: `$_runCommand`',
    '',
    '## Exact error message / assertion failure',
    '```text',
    '${result['error'] ?? ''}',
    '',
    '${result['traceback'] ?? ''}',
    '```',
    '',
    '## Relevant logs and observations',
    '```json',
    const JsonEncoder.withIndent('  ')
        .convert(<String, Object?>{'steps': null})
        .replaceFirst(
          '{\n  "steps": null\n}',
          const JsonEncoder.withIndent('  ').convert(<String, Object?>{
            'active_local_workspace_id': result['active_local_workspace_id'],
            'inactive_hosted_workspace_id':
                result['inactive_hosted_workspace_id'],
            'active_local_repository_path':
                result['active_local_repository_path'],
            'visible_texts_in_switcher': result['visible_texts_in_switcher'],
            'visible_semantics_in_switcher':
                result['visible_semantics_in_switcher'],
            'visible_texts_in_settings': result['visible_texts_in_settings'],
            'visible_semantics_in_settings':
                result['visible_semantics_in_settings'],
            'repository_path_value_in_settings':
                result['repository_path_value_in_settings'],
            'write_branch_value_in_settings':
                result['write_branch_value_in_settings'],
            'visible_texts_after_connect_attempt':
                result['visible_texts_after_connect_attempt'],
            'visible_semantics_after_connect_attempt':
                result['visible_semantics_after_connect_attempt'],
          }),
        ),
    '```',
  ].join('\n');
}

List<String> _bugReproductionLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<dynamic>? ?? const <dynamic>[])
      .whereType<Map<Object?, Object?>>();
  final lines = <String>[
    '1. Configure a local workspace with a valid local repository path. ${_stepOutcome(steps, 2, fallback: 'Observed together with the active local metadata checks in the seeded production runtime.')}',
    '2. Set this workspace as the active workspace. ${_stepOutcome(steps, 1, fallback: 'The production runtime opened with the seeded local workspace active.')}',
    '3. Open the workspace switcher. ${_stepOutcome(steps, 1, fallback: 'The workspace switcher did not expose the expected active local state.')}',
    '4. Inspect the labels and controls for the active local workspace row. ${_stepOutcome(steps, 2, fallback: 'The active local row or its associated sign-in controls did not match the expected visible state.')}',
    '5. Open Settings from the active local workspace and inspect the Repository access surface for the visible `Connect GitHub` control. ${_stepOutcome(steps, 3, fallback: 'The Repository access surface did not preserve the expected local metadata and sign-in affordance.')}',
    '6. Tap `Connect GitHub` and verify the sign-in dialog opens without losing the local metadata when dismissed. ${_stepOutcome(steps, 4, fallback: 'The Connect GitHub flow was not usable from the active local workspace.')}',
  ];
  return lines;
}

String _stepOutcome(
  Iterable<Map<Object?, Object?>> steps,
  int stepNumber, {
  required String fallback,
}) {
  final step = steps.cast<Map<Object?, Object?>?>().firstWhere(
    (candidate) => candidate?['step'] == stepNumber,
    orElse: () => null,
  );
  if (step == null) {
    return '❌ $fallback';
  }
  final marker = step['status'] == 'passed' ? '✅' : '❌';
  return '$marker ${step['observed']}';
}

String _actualResult(Map<String, Object?> result) {
  final failed = _failedStep(result);
  if (failed.isNotEmpty) {
    return failed;
  }
  return 'The scenario did not match the expected result.';
}

List<String> _stepLines(Map<String, Object?> result, {required bool jira}) {
  final steps = result['steps'];
  if (steps is! List) {
    return <String>[jira ? '* <no step data>' : '- <no step data>'];
  }
  return steps
      .whereType<Map<Object?, Object?>>()
      .map((step) {
        final marker = step['status'] == 'passed' ? '✅' : '❌';
        final text =
            '$marker Step ${step['step']}: ${step['action']} Observed: ${step['observed']}';
        return jira ? '* ${_jiraEscape(text)}' : '- $text';
      })
      .toList(growable: false);
}

List<String> _humanVerificationLines(
  Map<String, Object?> result, {
  required bool jira,
}) {
  final checks = result['human_verification'];
  if (checks is! List) {
    return <String>[
      jira
          ? '* <no human verification data>'
          : '- <no human verification data>',
    ];
  }
  return checks
      .whereType<Map<Object?, Object?>>()
      .map((check) {
        final text =
            'Checked: ${check['check']} Observed: ${check['observed']}';
        return jira ? '* ${_jiraEscape(text)}' : '- $text';
      })
      .toList(growable: false);
}

String _failedStep(Map<String, Object?> result) {
  final steps = result['steps'];
  if (steps is! List) {
    return '';
  }
  final failed = steps
      .whereType<Map<Object?, Object?>>()
      .where((step) => step['status'] == 'failed')
      .toList(growable: false);
  if (failed.isEmpty) {
    return '';
  }
  return failed
      .map(
        (step) =>
            'Step ${step['step']}: ${step['action']} Observed: ${step['observed']}',
      )
      .join(' ');
}

String _jiraEscape(String text) =>
    text.replaceAll('{', '\\{').replaceAll('}', '\\}');

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
