import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support/ts725_local_hosted_workspace_fixture.dart';

const String _ticketKey = 'TS-725';
const String _ticketSummary =
    'Inactive workspace state - deterministic display vs live active state';
const String _runCommand =
    'flutter test testing/tests/TS-725/test_ts_725.dart --reporter expanded';
const String _authToken = 'ghp_ts725_widget_token';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-725 active local state stays live while inactive hosted state stays deterministic',
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
      Ts725LocalHostedWorkspaceFixture? fixture;
      Ts725LocalHostedWorkspaceScreen? screen;

      try {
        fixture = await Ts725LocalHostedWorkspaceFixture.create(tester);
        screen = await fixture.launch();
        await screen.waitForReady(
          Ts725LocalHostedWorkspaceFixture.activeLocalDisplayName,
        );

        result['active_local_workspace_id'] = fixture.activeLocalWorkspace.id;
        result['inactive_hosted_workspace_id'] =
            fixture.inactiveHostedWorkspace.id;
        result['active_local_repository_path'] =
            fixture.activeLocalRepositoryPath;
        result['inactive_hosted_repository'] =
            Ts725LocalHostedWorkspaceFixture.inactiveHostedRepository;

        await screen.openWorkspaceSwitcher();
        final workspaceState = await fixture.loadWorkspaceState();
        result['active_workspace_id'] = workspaceState.activeWorkspaceId;
        result['visible_texts_before_sign_in'] = screen.visibleTexts();
        result['visible_semantics_before_sign_in'] = screen
            .visibleSemanticsLabelsSnapshot();

        final failures = <String>[];

        final step1Observed =
            'switcher_visible=${screen.isWorkspaceSwitcherVisible}; '
            'active_workspace=${workspaceState.activeWorkspaceId}; '
            'visible_texts=${_formatList(screen.visibleTexts())}';
        _recordStep(
          result,
          step: 1,
          status: screen.isWorkspaceSwitcherVisible ? 'passed' : 'failed',
          action: 'Open the workspace switcher.',
          observed: step1Observed,
        );
        if (!screen.isWorkspaceSwitcherVisible) {
          failures.add(
            'Step 1 failed: the workspace switcher did not open from the active local workspace.\n'
            'Observed: $step1Observed',
          );
        }

        final activeLocalObserved =
            'selected=${workspaceState.activeWorkspaceId == fixture.activeLocalWorkspace.id}; '
            'has_local_type=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Local')}; '
            'has_local_git_state=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Local Git')}; '
            'has_active_label=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Active')}; '
            'has_open_button=${screen.canOpenWorkspace(fixture.activeLocalWorkspace.id)}';
        final activeLocalMatches =
            workspaceState.activeWorkspaceId ==
                fixture.activeLocalWorkspace.id &&
            screen.workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Local',
            ) &&
            screen.workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Local Git',
            ) &&
            screen.workspaceRowContainsText(
              fixture.activeLocalWorkspace.id,
              'Active',
            ) &&
            !screen.canOpenWorkspace(fixture.activeLocalWorkspace.id);
        _recordStep(
          result,
          step: 2,
          status: activeLocalMatches ? 'passed' : 'failed',
          action: 'Inspect the active local workspace row.',
          observed: activeLocalObserved,
        );
        if (!activeLocalMatches) {
          failures.add(
            'Step 2 failed: the active local row did not show the expected live Local Git state.\n'
            'Observed: $activeLocalObserved',
          );
        }

        final inactiveHostedObserved =
            'has_hosted_type=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Hosted')}; '
            'has_needs_sign_in=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Needs sign-in')}; '
            'has_open_button=${screen.canOpenWorkspace(fixture.inactiveHostedWorkspace.id)}; '
            'shows_connected=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Connected')}; '
            'shows_read_only=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Read-only')}; '
            'shows_attachments_limited=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Attachments limited')}';
        final inactiveHostedMatches =
            screen.workspaceRowContainsText(
              fixture.inactiveHostedWorkspace.id,
              'Hosted',
            ) &&
            screen.workspaceRowContainsText(
              fixture.inactiveHostedWorkspace.id,
              'Needs sign-in',
            ) &&
            screen.canOpenWorkspace(fixture.inactiveHostedWorkspace.id) &&
            !screen.workspaceRowContainsText(
              fixture.inactiveHostedWorkspace.id,
              'Connected',
            ) &&
            !screen.workspaceRowContainsText(
              fixture.inactiveHostedWorkspace.id,
              'Read-only',
            ) &&
            !screen.workspaceRowContainsText(
              fixture.inactiveHostedWorkspace.id,
              'Attachments limited',
            );
        _recordStep(
          result,
          step: 3,
          status: inactiveHostedMatches ? 'passed' : 'failed',
          action: 'Inspect the inactive hosted workspace row.',
          observed: inactiveHostedObserved,
        );
        if (!inactiveHostedMatches) {
          failures.add(
            'Step 3 failed: the inactive hosted row did not stay in the deterministic Needs sign-in state before sign-in.\n'
            'Observed: $inactiveHostedObserved',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the workspace switcher before signing in and compared the active local row with the inactive hosted row.',
          observed:
              'active_local_row=Local + Local Git + Active; inactive_hosted_row=Hosted + Needs sign-in + Open workspace; visible_texts=${_formatList(screen.visibleTexts())}',
        );

        await screen.closeWorkspaceSwitcher();
        await screen.openSettings();

        final connectGitHubVisible =
            screen.isControlVisible('Connect GitHub') ||
            screen.isTextVisible('Connect GitHub') ||
            screen.isSemanticsLabelVisible('Connect GitHub');
        final repositoryAccessVisible =
            screen.isTextVisible('Repository access') ||
            screen.isSemanticsLabelVisible('Repository access');
        result['visible_texts_in_settings'] = screen.visibleTexts();
        result['visible_semantics_in_settings'] = screen
            .visibleSemanticsLabelsSnapshot();

        var tappedConnectGitHub = false;
        var tokenFieldVisible = false;
        var connectTokenVisible = false;
        var tappedConnectToken = false;
        var postAuthAccessStateVisible = false;
        var switcherReopenedAfterAuth = false;
        var step4FailureReason =
            'the active local workspace shows Repository access but exposes no production-visible Connect GitHub control, so TS-725 cannot perform the required sign-in step from the active local runtime.';
        String? step5Observed;
        var postAuthActiveLocalMatches = false;
        var postAuthInactiveHostedMatches = false;

        if (connectGitHubVisible) {
          tappedConnectGitHub = await screen.tapVisibleControl(
            'Connect GitHub',
          );
          if (!tappedConnectGitHub) {
            step4FailureReason =
                'the active local workspace exposed Connect GitHub text, but the production control could not be activated to start the ticketed sign-in flow.';
          } else {
            final authFormVisible = await screen.waitForAnyVisibleText(const [
              'Fine-grained token',
              'Connect token',
            ]);
            tokenFieldVisible =
                authFormVisible &&
                screen.isLabeledTextFieldVisible('Fine-grained token');
            connectTokenVisible =
                authFormVisible && screen.isControlVisible('Connect token');

            if (!tokenFieldVisible || !connectTokenVisible) {
              step4FailureReason =
                  'tapping Connect GitHub did not expose the production token form needed to complete the ticketed sign-in flow.';
            } else {
              await screen.enterLabeledTextField(
                'Fine-grained token',
                text: _authToken,
              );
              tappedConnectToken = await screen.tapVisibleControl(
                'Connect token',
              );
              postAuthAccessStateVisible =
                  tappedConnectToken &&
                  await screen.waitForAnyVisibleText(const [
                    'Connected',
                    'Read-only',
                    'Attachments limited',
                  ]);

              result['visible_texts_after_auth_attempt'] = screen
                  .visibleTexts();
              result['visible_semantics_after_auth_attempt'] = screen
                  .visibleSemanticsLabelsSnapshot();

              if (!postAuthAccessStateVisible) {
                step4FailureReason =
                    'submitting the production token form did not produce a visible post-auth repository access state, so the test could not prove the sign-in transition completed.';
              } else {
                try {
                  await screen.openWorkspaceSwitcher();
                  switcherReopenedAfterAuth = screen.isWorkspaceSwitcherVisible;
                } on TestFailure {
                  switcherReopenedAfterAuth = false;
                }

                if (!switcherReopenedAfterAuth) {
                  step4FailureReason =
                      'the sign-in controls completed, but Workspace switcher could not be reopened from the still-active local workspace.';
                } else {
                  final postAuthWorkspaceState = await fixture
                      .loadWorkspaceState();
                  result['active_workspace_id_after_sign_in'] =
                      postAuthWorkspaceState.activeWorkspaceId;
                  result['visible_texts_after_sign_in'] = screen.visibleTexts();
                  result['visible_semantics_after_sign_in'] = screen
                      .visibleSemanticsLabelsSnapshot();

                  postAuthActiveLocalMatches =
                      postAuthWorkspaceState.activeWorkspaceId ==
                          fixture.activeLocalWorkspace.id &&
                      screen.workspaceRowContainsText(
                        fixture.activeLocalWorkspace.id,
                        'Local',
                      ) &&
                      screen.workspaceRowContainsText(
                        fixture.activeLocalWorkspace.id,
                        'Local Git',
                      ) &&
                      screen.workspaceRowContainsText(
                        fixture.activeLocalWorkspace.id,
                        'Active',
                      ) &&
                      !screen.canOpenWorkspace(fixture.activeLocalWorkspace.id);
                  postAuthInactiveHostedMatches =
                      screen.workspaceRowContainsText(
                        fixture.inactiveHostedWorkspace.id,
                        'Hosted',
                      ) &&
                      screen.workspaceRowContainsText(
                        fixture.inactiveHostedWorkspace.id,
                        'Needs sign-in',
                      ) &&
                      screen.canOpenWorkspace(
                        fixture.inactiveHostedWorkspace.id,
                      ) &&
                      !screen.workspaceRowContainsText(
                        fixture.inactiveHostedWorkspace.id,
                        'Connected',
                      ) &&
                      !screen.workspaceRowContainsText(
                        fixture.inactiveHostedWorkspace.id,
                        'Read-only',
                      ) &&
                      !screen.workspaceRowContainsText(
                        fixture.inactiveHostedWorkspace.id,
                        'Attachments limited',
                      );

                  step5Observed =
                      'active_workspace=${postAuthWorkspaceState.activeWorkspaceId}; '
                      'active_local_has_local_type=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Local')}; '
                      'active_local_has_local_git_state=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Local Git')}; '
                      'active_local_has_active_label=${screen.workspaceRowContainsText(fixture.activeLocalWorkspace.id, 'Active')}; '
                      'active_local_has_open_button=${screen.canOpenWorkspace(fixture.activeLocalWorkspace.id)}; '
                      'inactive_hosted_has_hosted_type=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Hosted')}; '
                      'inactive_hosted_has_needs_sign_in=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Needs sign-in')}; '
                      'inactive_hosted_has_open_button=${screen.canOpenWorkspace(fixture.inactiveHostedWorkspace.id)}; '
                      'inactive_hosted_shows_connected=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Connected')}; '
                      'inactive_hosted_shows_read_only=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Read-only')}; '
                      'inactive_hosted_shows_attachments_limited=${screen.workspaceRowContainsText(fixture.inactiveHostedWorkspace.id, 'Attachments limited')}; '
                      'visible_texts=${_formatList(screen.visibleTexts())}';
                }
              }
            }
          }
        }

        final step4Observed =
            'connect_github_visible=$connectGitHubVisible; '
            'repository_access_visible=$repositoryAccessVisible; '
            'tapped_connect_github=$tappedConnectGitHub; '
            'token_field_visible=$tokenFieldVisible; '
            'connect_token_visible=$connectTokenVisible; '
            'tapped_connect_token=$tappedConnectToken; '
            'post_auth_access_state_visible=$postAuthAccessStateVisible; '
            'switcher_reopened_after_auth=$switcherReopenedAfterAuth; '
            'visible_texts=${_formatList(screen.visibleTexts())}; '
            'visible_semantics=${_formatList(screen.visibleSemanticsLabelsSnapshot())}';
        _recordStep(
          result,
          step: 4,
          status: switcherReopenedAfterAuth ? 'passed' : 'failed',
          action:
              'Sign in to GitHub from the active local workspace and re-open the switcher.',
          observed: step4Observed,
        );
        if (!switcherReopenedAfterAuth) {
          failures.add(
            'Step 4 failed: $step4FailureReason\n'
            'Observed: $step4Observed',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the active local workspace Settings surface to find the GitHub sign-in action required by the ticket.',
          observed:
              'connect_github_visible=$connectGitHubVisible; repository_access_visible=$repositoryAccessVisible; switcher_reopened_after_auth=$switcherReopenedAfterAuth',
        );

        _recordStep(
          result,
          step: 5,
          status:
              switcherReopenedAfterAuth &&
                  postAuthActiveLocalMatches &&
                  postAuthInactiveHostedMatches
              ? 'passed'
              : 'failed',
          action: 'Verify if the inactive hosted workspace state has changed.',
          observed:
              step5Observed ??
              'Post-auth validation did not run because the test could not complete the production GitHub sign-in transition and re-open Workspace switcher from the active local workspace. '
                  'Step 4 observed: $step4Observed',
        );

        if (!switcherReopenedAfterAuth) {
          failures.add(
            'Step 5 failed: the test did not re-open Workspace switcher after a real GitHub sign-in, so it could not verify the inactive hosted row after auth.\n'
            'Observed: ${step5Observed ?? step4Observed}',
          );
        } else if (!postAuthActiveLocalMatches ||
            !postAuthInactiveHostedMatches) {
          failures.add(
            'Step 5 failed: after a real GitHub sign-in, the workspace switcher did not preserve the expected active local and inactive hosted states.\n'
            'Observed: ${step5Observed ?? '<no post-auth observation recorded>'}',
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
  final error = '${result['error'] ?? 'AssertionError: TS-725 failed'}';
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
    '* Launched the production tracker in a supported Flutter widget runtime with one active local workspace and one inactive hosted workspace saved.',
    '* Opened *Workspace switcher* and verified the active local row showed {{Local Git}} while the inactive hosted row showed {{Needs sign-in}}.',
    "* Attempted the ticket's sign-in step from the active local workspace and only treats the scenario as passed after a real auth transition re-opens *Workspace switcher* for the post-auth assertion.",
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
    '- Launched the production tracker in a supported Flutter widget runtime with one active local workspace and one inactive hosted workspace saved.',
    '- Opened **Workspace switcher** and verified the active local row showed `Local Git` while the inactive hosted row showed `Needs sign-in`.',
    "- Attempted the ticket's sign-in step from the active local workspace and only treats the scenario as passed after a real auth transition re-opens **Workspace switcher** for the post-auth assertion.",
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
    '# $_ticketKey - Active local workspace cannot perform the required GitHub sign-in step',
    '',
    '## Reproduction steps',
    '1. Seed the production workspace profile store with one active local workspace and one inactive hosted workspace.',
    '2. Launch the production tracker in a supported runtime that can actually open the active local repository.',
    '3. Open **Workspace switcher** and confirm the active local row shows `Local Git` while the inactive hosted row shows `Needs sign-in`.',
    '4. From the still-active local workspace, open **Settings** and look for the production GitHub sign-in entry point needed by TS-725.',
    '',
    '## Expected result',
    'The active local workspace should expose a production-visible GitHub sign-in path so the ticket can perform the auth step, re-open the workspace switcher, and verify the inactive hosted row still stays `Needs sign-in` instead of changing to `Connected` or `Read-only`.',
    '',
    '## Actual result',
    "The active local workspace still renders the `Repository access` section in Settings, but it only shows `Local Git` and exposes no visible `Connect GitHub` control, so the ticket's sign-in step cannot be executed from the required active local scenario and the post-auth validation remains correctly failed.",
    '',
    '## Missing production capability',
    'When the active workspace is local (`supportsGitHubAuth == false` in production), the app hides the GitHub auth controls entirely. TS-725 requires signing in while that local workspace remains active, but the production UI does not expose any supported action to do that.',
    '',
    '## Failing command',
    '```bash',
    _runCommand,
    '```',
    '',
    '## Exact failure output',
    '```text',
    '${result['error'] ?? ''}',
    '```',
    '',
    '## Relevant observations',
    '```json',
    jsonEncode(<String, Object?>{
      'active_workspace_id': result['active_workspace_id'],
      'active_local_workspace_id': result['active_local_workspace_id'],
      'inactive_hosted_workspace_id': result['inactive_hosted_workspace_id'],
      'visible_texts_before_sign_in': result['visible_texts_before_sign_in'],
      'visible_texts_in_settings': result['visible_texts_in_settings'],
      'visible_semantics_in_settings': result['visible_semantics_in_settings'],
      'visible_texts_after_auth_attempt':
          result['visible_texts_after_auth_attempt'],
      'visible_semantics_after_auth_attempt':
          result['visible_semantics_after_auth_attempt'],
    }),
    '```',
  ].join('\n');
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
        final text = '${check['check']} Observed: ${check['observed']}';
        return jira ? '* ${_jiraEscape(text)}' : '- $text';
      })
      .toList(growable: false);
}

String _failedStep(Map<String, Object?> result) {
  final steps = result['steps'];
  if (steps is! List) {
    return '${result['error'] ?? ''}';
  }
  for (final step in steps.whereType<Map<Object?, Object?>>()) {
    if (step['status'] != 'passed') {
      return 'Step ${step['step']}: ${step['observed']}';
    }
  }
  return '${result['error'] ?? ''}';
}

String _formatList(List<String> values) => values.join(' || ');

String _jiraEscape(String value) =>
    value.replaceAll('{', '\\{').replaceAll('}', '\\}');
