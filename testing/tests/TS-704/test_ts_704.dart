import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../fixtures/workspace_onboarding_screen_fixture.dart';
import 'support/ts704_hosted_workspace_runtime.dart';

const String _ticketKey = 'TS-704';
const String _ticketSummary =
    'Post-save routing for hosted workspace opens the workspace and shows the in-context auth prompt';
const String _testFilePath = 'testing/tests/TS-704/test_ts_704.dart';
const String _runCommand =
    'flutter test testing/tests/TS-704/test_ts_704.dart --reporter expanded';
const String _currentWorkspaceRepository = 'owner/current';
const String _currentWorkspaceBranch = 'main';
const String _selectedRepository = 'owner/next-repo';
const String _selectedBranch = 'release';
const String _selectedWorkspaceId = 'hosted:owner/next-repo@release';
const String _disconnectedBannerTitle = 'GitHub write access is not connected';
const String _disconnectedBannerMessage =
    'Create, edit, comment, and status changes stay read-only until you connect GitHub with a fine-grained token that has repository Contents write access. PAT is the default browser path.';
const String _bannerActionLabel = 'Connect GitHub';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-704 saving a hosted workspace opens the selected workspace and shows the inline auth prompt',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      SharedPreferences.setMockInitialValues(const <String, Object>{
        'trackstate.githubToken.workspace.hosted%3Aowner%2Fcurrent%40main':
            'workspace-token',
      });
      final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 10, 0),
      );
      final openedRepositories = <String>[];
      const accessibleRepositories = <HostedRepositoryReference>[
        HostedRepositoryReference(
          fullName: _selectedRepository,
          defaultBranch: _selectedBranch,
        ),
        HostedRepositoryReference(
          fullName: 'owner/platform-foundation',
          defaultBranch: 'main',
        ),
      ];

      Future<TrackStateRepository> openHostedRepository({
        required String repository,
        required String defaultBranch,
        required String writeBranch,
      }) async {
        openedRepositories.add('$repository@$defaultBranch');
        return Ts704HostedWorkspaceRepository(
          snapshot: await createTs704Snapshot(
            repository: repository,
            branch: defaultBranch,
          ),
          provider: Ts704HostedProvider(
            repositoryName: repository,
            branch: defaultBranch,
            accessibleRepositories: accessibleRepositories,
          ),
        );
      }

      try {
        await workspaceProfileService.createProfile(
          const WorkspaceProfileInput(
            targetType: WorkspaceProfileTargetType.hosted,
            target: _currentWorkspaceRepository,
            defaultBranch: _currentWorkspaceBranch,
          ),
        );
        final bootstrapSnapshot = await createTs704Snapshot(
          repository: 'bootstrap/bootstrap',
          branch: 'main',
        );

        final screen = await launchWorkspaceOnboardingFixture(
          tester,
          repositoryFactory: () => Ts704HostedWorkspaceRepository(
            snapshot: bootstrapSnapshot,
            provider: Ts704HostedProvider(
              repositoryName: 'bootstrap/bootstrap',
              branch: 'main',
            ),
          ),
          workspaceProfileService: workspaceProfileService,
          openHostedRepository: openHostedRepository,
        );

        try {
          final initialState = screen.captureState();
          result['initial_opened_repository'] = openedRepositories.join(', ');
          result['initial_top_bar_access_label'] =
              initialState.repositoryAccessTopBarLabel;
          result['initial_visible_texts'] = initialState.visibleTexts.join(
            ' | ',
          );

          if (openedRepositories.isEmpty ||
              openedRepositories.first !=
                  '$_currentWorkspaceRepository@$_currentWorkspaceBranch') {
            throw AssertionError(
              'Precondition failed: the active hosted workspace did not open before the onboarding scenario started.\n'
              'Observed opened repositories: ${openedRepositories.join(', ')}',
            );
          }

          await screen.openAddWorkspace();
          await screen.chooseHostedRepository();

          final selectionState = screen.captureState();
          result['selection_visible_texts'] = selectionState.visibleTexts.join(
            ' | ',
          );

          final selectionFailures = <String>[];
          if (!selectionState.isOnboardingVisible) {
            selectionFailures.add(
              'The hosted onboarding sheet was not visible after choosing "Hosted repository".',
            );
          }
          if (!selectionState.visibleTexts.contains(_selectedRepository) ||
              !selectionState.visibleTexts.contains(
                'owner/platform-foundation',
              )) {
            selectionFailures.add(
              'The accessible repository suggestions did not show the expected hosted repositories. Visible texts: ${selectionState.visibleTexts.join(', ')}',
            );
          }
          if (!selectionState.visibleTexts.contains(
            'Select a repository from the current GitHub session or enter owner/repo manually.',
          )) {
            selectionFailures.add(
              'The hosted onboarding helper text was not visible alongside the repository suggestions.',
            );
          }
          _recordStep(
            result,
            step: 1,
            status: selectionFailures.isEmpty ? 'passed' : 'failed',
            action:
                "Complete the 'Hosted repository' onboarding form with valid details.",
            observed:
                'onboarding_visible=${selectionState.isOnboardingVisible}; accessible_repositories_present=${selectionState.visibleTexts.contains(_selectedRepository)}; helper_visible=${selectionState.visibleTexts.contains('Select a repository from the current GitHub session or enter owner/repo manually.')}; visible_texts=${selectionState.visibleTexts.join(' || ')}',
          );
          if (selectionFailures.isNotEmpty) {
            throw AssertionError(selectionFailures.join('\n'));
          }

          await screen.chooseHostedRepositorySuggestion(_selectedRepository);
          final prefilledState = screen.captureState();
          result['prefilled_repository'] = prefilledState.hostedRepositoryValue;
          result['prefilled_branch'] = prefilledState.hostedBranchValue;

          if (prefilledState.hostedRepositoryValue != _selectedRepository ||
              prefilledState.hostedBranchValue != _selectedBranch) {
            throw AssertionError(
              'Step 1 failed: selecting the visible hosted repository suggestion should prefill the onboarding form.\n'
              'Observed repository field: ${prefilledState.hostedRepositoryValue}\n'
              'Observed branch field: ${prefilledState.hostedBranchValue}',
            );
          }

          await screen.submit();

          final postOpenState = screen.captureState();
          final workspaceState = await workspaceProfileService.loadState();
          result['opened_repositories'] = openedRepositories.join(', ');
          result['post_open_dashboard_visible'] =
              postOpenState.isDashboardVisible;
          result['post_open_onboarding_visible'] =
              postOpenState.isOnboardingVisible;
          result['post_open_top_bar_access_label'] =
              postOpenState.repositoryAccessTopBarLabel;
          result['post_open_visible_texts'] = postOpenState.visibleTexts.join(
            ' | ',
          );
          result['active_workspace_id'] = workspaceState.activeWorkspaceId;
          result['active_workspace_target'] =
              workspaceState.activeWorkspace?.target;
          result['active_workspace_default_branch'] =
              workspaceState.activeWorkspace?.defaultBranch;
          result['access_callout_visible'] = screen.isAccessCalloutVisible(
            title: _disconnectedBannerTitle,
            message: _disconnectedBannerMessage,
          );
          result['access_callout_action_visible'] = screen
              .isAccessCalloutActionVisible(
                title: _disconnectedBannerTitle,
                message: _disconnectedBannerMessage,
                actionLabel: _bannerActionLabel,
              );

          final step2Failures = <String>[];
          if (openedRepositories.last !=
              '$_selectedRepository@$_selectedBranch') {
            step2Failures.add(
              'Clicking Open did not switch the runtime to the selected hosted repository. Observed opened repositories: ${openedRepositories.join(', ')}',
            );
          }
          if (workspaceState.activeWorkspaceId != _selectedWorkspaceId ||
              workspaceState.activeWorkspace?.target != _selectedRepository ||
              workspaceState.activeWorkspace?.defaultBranch !=
                  _selectedBranch) {
            step2Failures.add(
              'Clicking Open did not persist the selected hosted workspace as active. Observed active workspace: ${workspaceState.activeWorkspaceId} / ${workspaceState.activeWorkspace?.target}@${workspaceState.activeWorkspace?.defaultBranch}',
            );
          }
          _recordStep(
            result,
            step: 2,
            status: step2Failures.isEmpty ? 'passed' : 'failed',
            action: "Click the 'Save' or 'Open' button.",
            observed:
                'opened_repositories=${openedRepositories.join(', ')}; active_workspace=${workspaceState.activeWorkspaceId}; active_target=${workspaceState.activeWorkspace?.target}; active_branch=${workspaceState.activeWorkspace?.defaultBranch}',
          );
          if (step2Failures.isNotEmpty) {
            throw AssertionError(step2Failures.join('\n'));
          }

          final step3Failures = <String>[];
          final accessCalloutVisible = result['access_callout_visible'] == true;
          final accessActionVisible =
              result['access_callout_action_visible'] == true;
          if (!postOpenState.isDashboardVisible ||
              postOpenState.isOnboardingVisible) {
            step3Failures.add(
              'The app did not route back to the workspace dashboard after saving the hosted workspace. '
              'Observed dashboard visible: ${postOpenState.isDashboardVisible}; onboarding visible: ${postOpenState.isOnboardingVisible}.',
            );
          }
          if (!accessCalloutVisible ||
              !postOpenState.visibleTexts.contains(_disconnectedBannerTitle) ||
              !postOpenState.visibleTexts.contains(
                _disconnectedBannerMessage,
              ) ||
              !accessActionVisible) {
            step3Failures.add(
              'The disconnected hosted auth prompt was not shown inline for the new workspace. '
              'Observed access callout visible: $accessCalloutVisible; '
              'action visible: $accessActionVisible; '
              'top-bar access label: ${postOpenState.repositoryAccessTopBarLabel}; '
              'visible texts: ${postOpenState.visibleTexts.join(', ')}',
            );
          }
          _recordStep(
            result,
            step: 3,
            status: step3Failures.isEmpty ? 'passed' : 'failed',
            action: 'Observe the application routing and the Tracker UI.',
            observed:
                'dashboard_visible=${postOpenState.isDashboardVisible}; onboarding_visible=${postOpenState.isOnboardingVisible}; access_callout_visible=$accessCalloutVisible; access_action_visible=$accessActionVisible; top_bar_access_label=${postOpenState.repositoryAccessTopBarLabel}; visible_texts=${postOpenState.visibleTexts.join(' || ')}',
          );
          if (step3Failures.isNotEmpty) {
            throw AssertionError(step3Failures.join('\n'));
          }

          _recordHumanVerification(
            result,
            check:
                'Verified the post-save experience the way a hosted-workspace user would see it: the onboarding sheet closed, the dashboard was visible again, and the auth prompt stayed inline in the new workspace context.',
            observed:
                'dashboard_visible=${postOpenState.isDashboardVisible}; access_banner_visible=$accessCalloutVisible; access_banner_action_visible=$accessActionVisible; top_bar_access_label=${postOpenState.repositoryAccessTopBarLabel}',
          );
          _recordHumanVerification(
            result,
            check:
                'Verified the visible user-facing text in the auth prompt, including the warning title, the explanatory body copy, and the primary action.',
            observed:
                'title_present=${postOpenState.visibleTexts.contains(_disconnectedBannerTitle)}; message_present=${postOpenState.visibleTexts.contains(_disconnectedBannerMessage)}; action_present=${postOpenState.visibleTexts.contains(_bannerActionLabel)}',
          );

          _writePassOutputs(result);
        } finally {
          screen.dispose();
        }
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
    '* Seeded the production hosted workspace state with an existing active workspace for {noformat}$_currentWorkspaceRepository{noformat} on {noformat}$_currentWorkspaceBranch{noformat} and a stored GitHub token for that workspace session.',
    '* Opened Add workspace, switched the onboarding flow to {noformat}Hosted repository{noformat}, and selected the visible {noformat}$_selectedRepository{noformat} suggestion.',
    '* Clicked {noformat}Open{noformat} and verified the production WorkspaceProfileService made {noformat}$_selectedWorkspaceId{noformat} the active workspace.',
    '* Verified the Tracker UI returned to the workspace dashboard and immediately showed the in-context repository access prompt for the new hosted workspace.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: saving the hosted workspace routed directly into the selected workspace dashboard and showed the disconnected GitHub access prompt inline.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* URL: local Flutter widget runtime',
    '* Browser: none',
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
    '- Seeded the production hosted workspace state with an existing active workspace for `$_currentWorkspaceRepository` on `$_currentWorkspaceBranch` and a stored GitHub token for that workspace session.',
    '- Opened Add workspace, switched the onboarding flow to `Hosted repository`, and selected the visible `$_selectedRepository` suggestion.',
    '- Clicked `Open` and verified the production `WorkspaceProfileService` made `$_selectedWorkspaceId` the active workspace.',
    '- Verified the Tracker UI returned to the workspace dashboard and immediately showed the in-context repository access prompt for the new hosted workspace.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: saving the hosted workspace routed directly into the selected workspace dashboard and showed the disconnected GitHub access prompt inline.'
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
          ? 'Passed: saving the hosted workspace opened the selected workspace dashboard immediately and showed the disconnected GitHub access prompt inline.'
          : 'Failed: saving the hosted workspace did not open the selected workspace and auth prompt exactly as expected.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('URL: `local Flutter widget runtime`')
    ..writeln('Run command: `$_runCommand`');

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
    'Saving a hosted workspace from the onboarding flow does not fully complete the user-visible post-save experience. The selected hosted workspace is not opened and/or the in-context repository access prompt is not shown exactly where the new workspace should display it.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after completing the hosted repository onboarding flow for `$_selectedRepository` on `$_selectedBranch` and clicking `Open`, the app closes onboarding, opens the selected workspace dashboard, makes `$_selectedWorkspaceId` active, and immediately shows the inline repository access prompt with `$_disconnectedBannerTitle` plus the `$_bannerActionLabel` action.',
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
    '- URL: local Flutter widget runtime',
    '- Browser: none',
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '',
    '## Relevant Logs',
    '```text',
    'Initial opened repository: ${result['initial_opened_repository'] ?? '<missing>'}',
    'Opened repositories: ${result['opened_repositories'] ?? '<missing>'}',
    'Prefilled repository: ${result['prefilled_repository'] ?? '<missing>'}',
    'Prefilled branch: ${result['prefilled_branch'] ?? '<missing>'}',
    'Active workspace id: ${result['active_workspace_id'] ?? '<missing>'}',
    'Active workspace target: ${result['active_workspace_target'] ?? '<missing>'}',
    'Active workspace default branch: ${result['active_workspace_default_branch'] ?? '<missing>'}',
    'Dashboard visible: ${result['post_open_dashboard_visible'] ?? '<missing>'}',
    'Onboarding visible after open: ${result['post_open_onboarding_visible'] ?? '<missing>'}',
    'Top bar access label: ${result['post_open_top_bar_access_label'] ?? '<missing>'}',
    'Access callout visible: ${result['access_callout_visible'] ?? '<missing>'}',
    'Access callout action visible: ${result['access_callout_action_visible'] ?? '<missing>'}',
    'Visible texts after open: ${result['post_open_visible_texts'] ?? '<missing>'}',
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
      '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
          '   - Observed: ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  return 'the runtime opened `${result['opened_repositories'] ?? '<missing>'}`, the active workspace became `${result['active_workspace_id'] ?? '<missing>'}`, the dashboard visible flag was `${result['post_open_dashboard_visible'] ?? '<missing>'}`, the inline access callout visible flag was `${result['access_callout_visible'] ?? '<missing>'}`, and the user-facing texts after open were `${result['post_open_visible_texts'] ?? '<missing>'}`.';
}
