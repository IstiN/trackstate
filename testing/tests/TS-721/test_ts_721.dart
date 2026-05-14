import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../components/services/local_git_repository_service.dart';
import '../../fixtures/workspace_onboarding_screen_fixture.dart';
import 'support/ts721_cached_local_workspace_onboarding_service.dart';
import 'support/ts721_local_workspace_fixture.dart';
import 'support/ts721_recording_workspace_profile_service.dart';

const String _ticketKey = 'TS-721';
const String _ticketSummary =
    'Local onboarding completion automatically transitions to the Tracker UI';
const String _testFilePath = 'testing/tests/TS-721/test_ts_721.dart';
const String _runCommand =
    'flutter test testing/tests/TS-721/test_ts_721.dart --reporter expanded';
const String _readyStatus = 'Ready to open';
const String _readyMessage =
    'This folder already contains a committed TrackState workspace and is ready to open.';
const String _selectedFolderLabel = 'Selected folder';
const String _detailsTitle = 'Workspace details';
const String _workspaceNameLabel = 'Workspace name';
const String _writeBranchLabel = 'Write Branch';
const String _dashboardLabel = 'Dashboard';
const String _expectedAccessLabel = 'Local Git';
const String _expectedActionLabel = 'Open workspace';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-721 completing first-run local onboarding saves the workspace and opens the tracker',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };
      final fixture = await tester.runAsync(Ts721LocalWorkspaceFixture.create);
      if (fixture == null) {
        throw StateError('TS-721 fixture creation did not complete.');
      }
      final localWorkspaceInspection = await tester.runAsync(
        () => createLocalWorkspaceOnboardingService().inspectFolder(
          fixture.repositoryPath,
        ),
      );
      if (localWorkspaceInspection == null) {
        throw StateError('TS-721 local workspace inspection did not complete.');
      }
      final localWorkspaceOnboardingService =
          Ts721CachedLocalWorkspaceOnboardingService(
            inspection: localWorkspaceInspection,
          );
      final workspaceProfileService = Ts721RecordingWorkspaceProfileService(
        SharedPreferencesWorkspaceProfileService(
          now: () => DateTime.utc(2026, 5, 14, 12, 0),
        ),
      );
      final localRepositoryService = LocalGitRepositoryService(tester);
      final openedRepositories = <String>[];

      try {
        final localRepository = await localRepositoryService.openRepository(
          repositoryPath: fixture.repositoryPath,
        );
        final screen = await launchWorkspaceOnboardingFixture(
          tester,
          repositoryFactory: () => const DemoTrackStateRepository(),
          workspaceProfileService: workspaceProfileService,
          localWorkspaceOnboardingService: localWorkspaceOnboardingService,
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async {
                result['directory_picker_confirm_button'] = confirmButtonText;
                result['directory_picker_initial_directory'] = initialDirectory;
                return fixture.repositoryPath;
              },
          openLocalRepository:
              ({
                required String repositoryPath,
                required String defaultBranch,
                required String writeBranch,
              }) async {
                if (repositoryPath != fixture.repositoryPath) {
                  throw StateError(
                    'TS-721 expected to open "${fixture.repositoryPath}", but received "$repositoryPath".',
                  );
                }
                openedRepositories.add(
                  '$repositoryPath@$defaultBranch@$writeBranch',
                );
                return localRepository;
              },
        );

        try {
          final initialState = screen.captureState();
          result['initial_visible_texts'] = initialState.visibleTexts.join(
            ' | ',
          );

          if (!initialState.isOnboardingVisible ||
              !initialState.visibleTexts.contains('Add workspace') ||
              !initialState.visibleTexts.contains('Open existing folder') ||
              !initialState.visibleTexts.contains('Initialize folder')) {
            throw AssertionError(
              'Precondition failed: the first-run local onboarding screen was not visible.\n'
              'Observed visible texts: ${initialState.visibleTexts.join(', ')}',
            );
          }

          await screen.chooseOpenExistingFolder();
          final inspectedState = screen.captureState();
          print(
            'TS-721 debug inspected: folder=${inspectedState.localFolderPath}; '
            'name=${inspectedState.localWorkspaceNameValue}; '
            'branch=${inspectedState.localWriteBranchValue}; '
            'action=${inspectedState.primaryActionLabel}; '
            'texts=${inspectedState.visibleTexts.join(' || ')}',
          );
          result['inspected_folder_path'] = inspectedState.localFolderPath;
          result['inspected_workspace_name'] =
              inspectedState.localWorkspaceNameValue;
          result['inspected_write_branch'] =
              inspectedState.localWriteBranchValue;
          result['inspected_primary_action'] =
              inspectedState.primaryActionLabel;
          result['inspected_visible_texts'] = inspectedState.visibleTexts.join(
            ' | ',
          );

          await screen.enterLocalWorkspaceName(
            Ts721LocalWorkspaceFixture.expectedDisplayName,
          );
          await screen.enterLocalWriteBranch(
            Ts721LocalWorkspaceFixture.expectedBranch,
          );
          final editedState = screen.captureState();
          result['edited_workspace_name'] = editedState.localWorkspaceNameValue;
          result['edited_write_branch'] = editedState.localWriteBranchValue;

          final step1Failures = <String>[];
          if (!editedState.isOnboardingVisible) {
            step1Failures.add(
              'The local onboarding screen was no longer visible after selecting a valid folder.',
            );
          }
          if (editedState.localFolderPath != fixture.repositoryPath) {
            step1Failures.add(
              'The selected folder path did not match the repository returned by the directory picker. '
              'Observed folder path: ${editedState.localFolderPath}',
            );
          }
          if (inspectedState.localWriteBranchValue !=
              Ts721LocalWorkspaceFixture.expectedBranch) {
            step1Failures.add(
              'The detected local write branch did not prefill `${Ts721LocalWorkspaceFixture.expectedBranch}`. '
              'Observed branch: ${inspectedState.localWriteBranchValue}',
            );
          }
          if (editedState.localWorkspaceNameValue !=
              Ts721LocalWorkspaceFixture.expectedDisplayName) {
            step1Failures.add(
              'The local workspace name field did not retain the edited display name. '
              'Observed workspace name: ${editedState.localWorkspaceNameValue}',
            );
          }
          const requiredVisibleTexts = <String>[
            _readyStatus,
            _readyMessage,
            _selectedFolderLabel,
            _detailsTitle,
            _workspaceNameLabel,
            _writeBranchLabel,
          ];
          if (!editedState.visibleTexts.toSet().containsAll(
            requiredVisibleTexts,
          )) {
            step1Failures.add(
              'The onboarding details for a valid local workspace were not all visible. '
              'Observed texts: ${editedState.visibleTexts.join(', ')}',
            );
          }
          if (editedState.primaryActionLabel != _expectedActionLabel) {
            step1Failures.add(
              'The primary CTA did not stay on `$_expectedActionLabel`. '
              'Observed action: ${editedState.primaryActionLabel}',
            );
          }
          _recordStep(
            result,
            step: 1,
            status: step1Failures.isEmpty ? 'passed' : 'failed',
            action:
                'Complete the folder selection and details capture for a valid local workspace.',
            observed:
                'selected_folder=${editedState.localFolderPath}; workspace_name=${editedState.localWorkspaceNameValue}; write_branch=${editedState.localWriteBranchValue}; action_label=${editedState.primaryActionLabel}; visible_texts=${editedState.visibleTexts.join(' || ')}',
          );
          if (step1Failures.isNotEmpty) {
            throw AssertionError(step1Failures.join('\n'));
          }

          await screen.submit();

          final postOpenState = screen.captureState();
          final workspaceState = await workspaceProfileService.loadState();
          final createdInput =
              workspaceProfileService.createdInputs.singleOrNull;
          final activeWorkspace = workspaceState.activeWorkspace;
          final expectedWorkspaceInput = WorkspaceProfileInput(
            targetType: WorkspaceProfileTargetType.local,
            target: fixture.repositoryPath,
            defaultBranch: Ts721LocalWorkspaceFixture.expectedBranch,
            writeBranch: Ts721LocalWorkspaceFixture.expectedBranch,
            displayName: Ts721LocalWorkspaceFixture.expectedDisplayName,
          );
          final expectedWorkspaceId = WorkspaceProfile.create(
            expectedWorkspaceInput,
          ).id;

          result['create_profile_count'] =
              workspaceProfileService.createdInputs.length;
          result['create_profile_select_values'] = workspaceProfileService
              .createSelectValues
              .join(', ');
          result['create_profile_target'] = createdInput?.target;
          result['create_profile_default_branch'] = createdInput?.defaultBranch;
          result['create_profile_write_branch'] = createdInput?.writeBranch;
          result['create_profile_display_name'] = createdInput?.displayName;
          result['selected_workspace_ids'] = workspaceProfileService
              .selectedWorkspaceIds
              .join(', ');
          result['opened_repositories'] = openedRepositories.join(', ');
          result['active_workspace_id'] = workspaceState.activeWorkspaceId;
          result['active_workspace_target'] = activeWorkspace?.target;
          result['active_workspace_default_branch'] =
              activeWorkspace?.defaultBranch;
          result['active_workspace_display_name'] =
              activeWorkspace?.displayName;
          result['post_open_dashboard_visible'] =
              postOpenState.isDashboardVisible;
          result['post_open_onboarding_visible'] =
              postOpenState.isOnboardingVisible;
          result['post_open_access_label'] =
              postOpenState.repositoryAccessTopBarLabel;
          result['post_open_visible_texts'] = postOpenState.visibleTexts.join(
            ' | ',
          );

          final step2Failures = <String>[];
          if (workspaceProfileService.createdInputs.length != 1 ||
              createdInput == null) {
            step2Failures.add(
              'The onboarding flow did not call WorkspaceProfileService.createProfile exactly once. '
              'Observed create count: ${workspaceProfileService.createdInputs.length}',
            );
          } else {
            if (createdInput.targetType != WorkspaceProfileTargetType.local ||
                createdInput.target != fixture.repositoryPath ||
                createdInput.defaultBranch !=
                    Ts721LocalWorkspaceFixture.expectedBranch ||
                createdInput.writeBranch !=
                    Ts721LocalWorkspaceFixture.expectedBranch ||
                createdInput.displayName !=
                    Ts721LocalWorkspaceFixture.expectedDisplayName) {
              step2Failures.add(
                'WorkspaceProfileService.createProfile did not receive the expected local workspace input. '
                'Observed input: ${createdInput.targetType} / ${createdInput.target} / ${createdInput.defaultBranch} / ${createdInput.writeBranch} / ${createdInput.displayName}',
              );
            }
          }
          if (activeWorkspace?.id != expectedWorkspaceId ||
              activeWorkspace?.target != fixture.repositoryPath ||
              activeWorkspace?.defaultBranch !=
                  Ts721LocalWorkspaceFixture.expectedBranch ||
              activeWorkspace?.displayName !=
                  Ts721LocalWorkspaceFixture.expectedDisplayName) {
            step2Failures.add(
              'The saved workspace was not marked active after submission. '
              'Observed active workspace: ${activeWorkspace?.id} / ${activeWorkspace?.target} / ${activeWorkspace?.defaultBranch} / ${activeWorkspace?.displayName}',
            );
          }
          if (openedRepositories.lastOrNull !=
              '${fixture.repositoryPath}@${Ts721LocalWorkspaceFixture.expectedBranch}@${Ts721LocalWorkspaceFixture.expectedBranch}') {
            step2Failures.add(
              'Submitting the primary CTA did not open the selected local repository context. '
              'Observed opened repositories: ${openedRepositories.join(', ')}',
            );
          }
          _recordStep(
            result,
            step: 2,
            status: step2Failures.isEmpty ? 'passed' : 'failed',
            action:
                "Click the primary CTA (`$_expectedActionLabel`) to save and open the workspace.",
            observed:
                'create_profile_count=${workspaceProfileService.createdInputs.length}; create_profile_target=${createdInput?.target}; create_profile_display_name=${createdInput?.displayName}; active_workspace=${workspaceState.activeWorkspaceId}; opened_repositories=${openedRepositories.join(', ')}',
          );
          if (step2Failures.isNotEmpty) {
            throw AssertionError(step2Failures.join('\n'));
          }

          final step3Failures = <String>[];
          final dashboardVisibleInTexts = _visibleTextContains(
            postOpenState.visibleTexts,
            _dashboardLabel,
          );
          final issueSummaryVisible = _visibleTextContains(
            postOpenState.visibleTexts,
            Ts721LocalWorkspaceFixture.expectedIssueSummary,
          );
          if (!postOpenState.isDashboardVisible ||
              postOpenState.isOnboardingVisible) {
            step3Failures.add(
              'The app did not transition from onboarding into the Tracker dashboard immediately. '
              'Observed dashboard visible: ${postOpenState.isDashboardVisible}; onboarding visible: ${postOpenState.isOnboardingVisible}.',
            );
          }
          if (postOpenState.repositoryAccessTopBarLabel !=
              _expectedAccessLabel) {
            step3Failures.add(
              'The Tracker UI did not show the Local Git repository access label after onboarding. '
              'Observed access label: ${postOpenState.repositoryAccessTopBarLabel}',
            );
          }
          if (!dashboardVisibleInTexts || !issueSummaryVisible) {
            step3Failures.add(
              'The Tracker UI did not show the expected local repository context after onboarding. '
              'Observed visible texts: ${postOpenState.visibleTexts.join(', ')}',
            );
          }
          _recordStep(
            result,
            step: 3,
            status: step3Failures.isEmpty ? 'passed' : 'failed',
            action: 'Observe the app route and the Tracker UI state.',
            observed:
                'dashboard_visible=${postOpenState.isDashboardVisible}; onboarding_visible=${postOpenState.isOnboardingVisible}; access_label=${postOpenState.repositoryAccessTopBarLabel}; visible_texts=${postOpenState.visibleTexts.join(' || ')}',
          );
          if (step3Failures.isNotEmpty) {
            throw AssertionError(step3Failures.join('\n'));
          }

          _recordHumanVerification(
            result,
            check:
                'Verified the first-run onboarding experience the way a local-workspace user would see it: the form closed immediately after saving, the dashboard became visible, and the header switched to the Local Git context.',
            observed:
                'dashboard_visible=${postOpenState.isDashboardVisible}; access_label=${postOpenState.repositoryAccessTopBarLabel}; active_workspace=${workspaceState.activeWorkspaceId}',
          );
          _recordHumanVerification(
            result,
            check:
                'Verified the user-facing Tracker content from the selected local repository by checking the dashboard heading and the seeded issue summary rendered in the loaded workspace context.',
            observed:
                'dashboard_label_present=$dashboardVisibleInTexts; issue_summary_present=$issueSummaryVisible; visible_texts=${postOpenState.visibleTexts.join(' || ')}',
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
      } finally {
        await tester.runAsync(fixture.dispose);
      }
    },
    timeout: const Timeout(Duration(seconds: 60)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

bool _visibleTextContains(List<String> visibleTexts, String expectedText) {
  return visibleTexts.any(
    (text) => text == expectedText || text.contains(expectedText),
  );
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
    '* Launched the production first-run local onboarding flow with no saved workspaces and selected a valid Local Git repository through the folder picker.',
    '* Completed the local workspace details, clicked {noformat}$_expectedActionLabel{noformat}, and recorded the production {noformat}WorkspaceProfileService.createProfile{noformat} input.',
    '* Verified the saved workspace became active and the runtime opened the selected local repository immediately.',
    '* Verified the Tracker UI routed to the dashboard and rendered the Local Git repository context from the selected workspace.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: completing local onboarding saved the workspace profile, marked it active, and opened the Tracker dashboard immediately in the selected Local Git context.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* URL: local Flutter widget runtime',
    '* Browser: none',
    '* Repository path: {noformat}${result['inspected_folder_path'] ?? '<missing>'}{noformat}',
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
    '- Launched the production first-run local onboarding flow with no saved workspaces and selected a valid Local Git repository through the folder picker.',
    '- Completed the local workspace details, clicked `$_expectedActionLabel`, and recorded the production `WorkspaceProfileService.createProfile` input.',
    '- Verified the saved workspace became active and the runtime opened the selected local repository immediately.',
    '- Verified the Tracker UI routed to the dashboard and rendered the Local Git repository context from the selected workspace.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: completing local onboarding saved the workspace profile, marked it active, and opened the Tracker dashboard immediately in the selected Local Git context.'
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
          ? 'Passed: completing first-run local onboarding saved the workspace profile, activated the selected Local Git repository, and opened the Tracker dashboard immediately.'
          : 'Failed: completing first-run local onboarding did not save and open the selected local workspace exactly as expected.',
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
    'Completing the first-run local onboarding flow does not fully save and open the selected Local Git workspace. The production flow either fails to persist the new workspace as active, fails to leave onboarding, or fails to render the selected local repository context in the Tracker UI.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after selecting a valid local workspace folder, filling the workspace details, and clicking `$_expectedActionLabel`, the app should call `WorkspaceProfileService.createProfile` for the local repository, make `${result['active_workspace_id'] ?? '<expected active workspace>'}` active, close onboarding, and show the Tracker dashboard with the Local Git access state plus the selected repository content.',
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
    '- Repository path: `${result['inspected_folder_path'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Directory picker confirm button: ${result['directory_picker_confirm_button'] ?? '<missing>'}',
    'Create profile count: ${result['create_profile_count'] ?? '<missing>'}',
    'Create profile target: ${result['create_profile_target'] ?? '<missing>'}',
    'Create profile default branch: ${result['create_profile_default_branch'] ?? '<missing>'}',
    'Create profile write branch: ${result['create_profile_write_branch'] ?? '<missing>'}',
    'Create profile display name: ${result['create_profile_display_name'] ?? '<missing>'}',
    'Selected workspace ids: ${result['selected_workspace_ids'] ?? '<missing>'}',
    'Opened repositories: ${result['opened_repositories'] ?? '<missing>'}',
    'Active workspace id: ${result['active_workspace_id'] ?? '<missing>'}',
    'Active workspace target: ${result['active_workspace_target'] ?? '<missing>'}',
    'Active workspace default branch: ${result['active_workspace_default_branch'] ?? '<missing>'}',
    'Active workspace display name: ${result['active_workspace_display_name'] ?? '<missing>'}',
    'Dashboard visible: ${result['post_open_dashboard_visible'] ?? '<missing>'}',
    'Onboarding visible after submit: ${result['post_open_onboarding_visible'] ?? '<missing>'}',
    'Access label after submit: ${result['post_open_access_label'] ?? '<missing>'}',
    'Visible texts after submit: ${result['post_open_visible_texts'] ?? '<missing>'}',
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
  return 'after clicking `$_expectedActionLabel`, the flow observed create-profile count `${result['create_profile_count'] ?? '<missing>'}`, active workspace `${result['active_workspace_id'] ?? '<missing>'}`, access label `${result['post_open_access_label'] ?? '<missing>'}`, and visible texts `${result['post_open_visible_texts'] ?? '<missing>'}`.';
}
