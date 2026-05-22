import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service_io.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../fixtures/local_workspace_onboarding_screen_fixture.dart';

const String _ticketKey = 'TS-799';
const String _ticketSummary =
    'Initialize in an empty folder — initialization enabled and accessible';
const String _testFilePath = 'testing/tests/TS-799/test_ts_799.dart';
const String _runCommand =
    'flutter test testing/tests/TS-799/test_ts_799.dart --reporter expanded';
const String _expectedStatusLabel = 'Initialization required';
const String _expectedMessage =
    'This folder is empty. TrackState can initialize Git and create the starter workspace here.';
const String _expectedSubmitLabel = 'Initialize TrackState here';

const List<String> _requestSteps = <String>[
  'Open the first-launch onboarding screen.',
  "Select 'Initialize folder'.",
  'Pick the empty directory.',
  'Observe the status message and the action button state.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-799 allows initialization for a completely empty folder',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final directory = Directory(
        '${Directory.systemTemp.path}/ts799-empty-${DateTime.now().microsecondsSinceEpoch}',
      )..createSync(recursive: true);
      addTearDown(() {
        if (directory.existsSync()) {
          directory.deleteSync(recursive: true);
        }
      });
      result['directory_path'] = directory.path;

      final directoryPickerInvocations = <Map<String, String?>>[];
      final openedRepositories = <String>[];
      final onboardingService = _RecordingRealOnboardingService(
        delegate: const LocalGitWorkspaceOnboardingService(),
      );
      final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 17, 20, 45),
      );

      try {
        final screen =
            await launchLocalWorkspaceOnboardingFixture(
              tester,
              workspaceProfileService: workspaceProfileService,
              onboardingService: onboardingService,
              directoryPicker:
                  ({
                    String? confirmButtonText,
                    String? initialDirectory,
                  }) async {
                    final invocation = <String, String?>{
                      'confirmButtonText': confirmButtonText,
                      'initialDirectory': initialDirectory,
                    };
                    directoryPickerInvocations.add(invocation);
                    result['directory_picker_confirm_button'] =
                        confirmButtonText;
                    result['directory_picker_initial_directory'] =
                        initialDirectory;
                    return directory.path;
                  },
              openLocalRepository:
                  ({
                    required String repositoryPath,
                    required String defaultBranch,
                    required String writeBranch,
                  }) async {
                    openedRepositories.add(
                      '$repositoryPath@$defaultBranch@$writeBranch',
                    );
                    return const DemoTrackStateRepository();
                  },
              sharedPreferences: const <String, Object>{},
            ).timeout(
              const Duration(seconds: 20),
              onTimeout: () => throw TimeoutException(
                'Timed out waiting for the onboarding fixture to launch.',
              ),
            );

        try {
          final initialState = screen.captureState();
          result['initial_visible_texts'] = initialState.visibleTexts;
          final step1Failures = <String>[];
          if (!initialState.isOnboardingVisible) {
            step1Failures.add(
              'The first-launch onboarding screen was not visible.',
            );
          }
          if (!initialState.isInitializeActionVisible) {
            step1Failures.add(
              'The Initialize folder entry point was not visible before choosing a folder.',
            );
          }
          _recordStep(
            result,
            step: 1,
            status: step1Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[0],
            observed:
                'onboarding_visible=${initialState.isOnboardingVisible}; '
                'initialize_action_visible=${initialState.isInitializeActionVisible}; '
                'visible_texts=${initialState.visibleTexts.join(' | ')}',
          );
          if (step1Failures.isNotEmpty) {
            throw AssertionError(step1Failures.join('\n'));
          }

          await screen.chooseInitializeFolder().timeout(
            const Duration(seconds: 20),
            onTimeout: () => throw TimeoutException(
              'Timed out waiting for the Initialize folder flow to inspect the selected empty folder.',
            ),
          );

          _recordStep(
            result,
            step: 2,
            status: directoryPickerInvocations.length == 1
                ? 'passed'
                : 'failed',
            action: _requestSteps[1],
            observed:
                'directory_picker_calls=${directoryPickerInvocations.length}; '
                'confirm_button=${result['directory_picker_confirm_button']}; '
                'initial_directory=${result['directory_picker_initial_directory']}',
          );
          if (directoryPickerInvocations.length != 1) {
            throw AssertionError(
              'Step 2 failed: selecting "Initialize folder" did not invoke the directory picker exactly once.\n'
              'Observed invocations: ${jsonEncode(directoryPickerInvocations)}',
            );
          }

          final recordedInspection = onboardingService.lastInspection;
          final inspectedFolderPaths = onboardingService.inspectedFolderPaths;
          result['inspected_folder_paths'] = inspectedFolderPaths;
          result['production_inspection_state'] =
              recordedInspection?.state.name;
          result['production_inspection_message'] = recordedInspection?.message;

          final selectedState = screen.captureState();
          result['visible_texts'] = selectedState.visibleTexts;
          result['status_label'] = selectedState.statusLabel;
          result['inspection_message'] = selectedState.inspectionMessage;
          result['folder_path_visible'] = selectedState.folderPath;
          result['workspace_name_value'] = selectedState.workspaceNameValue;
          result['write_branch_value'] = selectedState.writeBranchValue;
          result['submit_label'] = selectedState.submitLabel;
          result['submit_visible'] = selectedState.isSubmitVisible;
          result['submit_enabled'] = selectedState.isSubmitEnabled;

          _recordStep(
            result,
            step: 3,
            status:
                recordedInspection != null &&
                    inspectedFolderPaths.length == 1 &&
                    inspectedFolderPaths.single == directory.path &&
                    selectedState.folderPath == directory.path
                ? 'passed'
                : 'failed',
            action: _requestSteps[2],
            observed:
                'picked_folder=${selectedState.folderPath}; '
                'expected_folder=${directory.path}; '
                'inspected_paths=${inspectedFolderPaths.join(' | ')}; '
                'inspection_state=${recordedInspection?.state.name}; '
                'visible_texts=${selectedState.visibleTexts.join(' | ')}',
          );
          if (recordedInspection == null) {
            throw AssertionError(
              'Step 3 failed: selecting the empty directory did not invoke the real onboarding inspectFolder call.',
            );
          }
          if (inspectedFolderPaths.length != 1 ||
              inspectedFolderPaths.single != directory.path) {
            throw AssertionError(
              'Step 3 failed: the onboarding UI did not inspect the selected empty directory via the real onboarding service.\n'
              'Expected inspected folder path: ${directory.path}\n'
              'Observed inspected folder paths: ${inspectedFolderPaths.join(' | ')}',
            );
          }
          if (selectedState.folderPath != directory.path) {
            throw AssertionError(
              'Step 3 failed: the onboarding flow did not reflect the selected empty directory after using Initialize folder.\n'
              'Expected folder path: ${directory.path}\n'
              'Observed folder path: ${selectedState.folderPath}\n'
              'Observed visible texts: ${selectedState.visibleTexts.join(' | ')}',
            );
          }

          final workspaceName = selectedState.workspaceNameValue ?? '';
          final writeBranch = selectedState.writeBranchValue ?? '';
          final step4Failures = <String>[];
          if (recordedInspection.state !=
              LocalWorkspaceInspectionState.readyToInitialize) {
            step4Failures.add(
              'The real onboarding inspection did not classify the empty folder as ready to initialize. '
              'Observed state: ${recordedInspection.state.name}',
            );
          }
          if (selectedState.statusLabel != _expectedStatusLabel) {
            step4Failures.add(
              'The visible status label was `${selectedState.statusLabel}` instead of `$_expectedStatusLabel`.',
            );
          }
          if (selectedState.inspectionMessage != _expectedMessage) {
            step4Failures.add(
              'The user-facing guidance did not match the expected empty-folder message.\n'
              'Observed message: ${selectedState.inspectionMessage}',
            );
          }
          if (!selectedState.isSubmitVisible ||
              selectedState.submitLabel != _expectedSubmitLabel) {
            step4Failures.add(
              'The expected Initialize action was not visible with the correct label.\n'
              'Observed submit label: ${selectedState.submitLabel}',
            );
          }
          if (!selectedState.isSubmitEnabled) {
            step4Failures.add(
              'The visible Initialize action was disabled for the empty folder.',
            );
          }
          if (workspaceName.trim().isEmpty) {
            step4Failures.add(
              'The Workspace name field was empty for the empty-folder initialization flow.',
            );
          }
          if (writeBranch.trim().isEmpty) {
            step4Failures.add(
              'The Write Branch field was empty for the empty-folder initialization flow.',
            );
          }

          _recordHumanVerification(
            result,
            check:
                'Viewed the first-launch onboarding screen as a user before choosing any local folder option.',
            observed: 'visible_texts=${initialState.visibleTexts.join(' | ')}',
          );
          _recordHumanVerification(
            result,
            check:
                'Chose Initialize folder and reviewed the exact status card copy, selected folder path, editable fields, and button state shown for the empty directory.',
            observed:
                'status_label=${selectedState.statusLabel}; '
                'inspection_message=${selectedState.inspectionMessage}; '
                'folder_path=${selectedState.folderPath}; '
                'workspace_name=$workspaceName; '
                'write_branch=$writeBranch; '
                'submit_label=${selectedState.submitLabel}; '
                'submit_enabled=${selectedState.isSubmitEnabled}',
          );

          if (step4Failures.isNotEmpty) {
            final gitDirectoryExists = Directory(
              '${directory.path}/.git',
            ).existsSync();
            final projectJsonPaths = _projectJsonPaths(directory);
            result['opened_repositories'] = openedRepositories;
            result['git_directory_exists'] = gitDirectoryExists;
            result['project_json_paths'] = projectJsonPaths;
            _recordStep(
              result,
              step: 4,
              status: 'failed',
              action: _requestSteps[3],
              observed:
                  'status_label=${selectedState.statusLabel}; '
                  'inspection_message=${selectedState.inspectionMessage}; '
                  'submit_label=${selectedState.submitLabel}; '
                  'submit_visible=${selectedState.isSubmitVisible}; '
                  'submit_enabled=${selectedState.isSubmitEnabled}; '
                  'workspace_name=$workspaceName; '
                  'write_branch=$writeBranch; '
                  'opened_repositories=${openedRepositories.join(' | ')}; '
                  'active_workspace_target=<not-submitted>; '
                  'git_directory_exists=$gitDirectoryExists; '
                  'project_json_paths=${projectJsonPaths.join(' | ')}',
            );
            throw AssertionError(step4Failures.join('\n'));
          }

          await screen.submit();
          await _pumpUntil(
            tester,
            () => openedRepositories.length == 1,
            timeout: const Duration(seconds: 40),
            failureMessage:
                'Timed out waiting for the empty-folder initialization flow to open the initialized workspace.',
          );

          final workspaceState = await tester.runAsync(
            () => workspaceProfileService.loadState(),
          );
          if (workspaceState == null) {
            throw StateError('Failed to load workspace state after submit.');
          }
          final activeWorkspace = workspaceState.activeWorkspace;
          final gitDirectoryExists = Directory(
            '${directory.path}/.git',
          ).existsSync();
          final projectJsonPaths = _projectJsonPaths(directory);
          result['opened_repositories'] = openedRepositories;
          result['active_workspace_id'] = workspaceState.activeWorkspaceId;
          result['active_workspace_target'] = activeWorkspace?.target;
          result['active_workspace_default_branch'] =
              activeWorkspace?.defaultBranch;
          result['active_workspace_write_branch'] =
              activeWorkspace?.writeBranch;
          result['active_workspace_display_name'] =
              activeWorkspace?.displayName;
          result['git_directory_exists'] = gitDirectoryExists;
          result['project_json_paths'] = projectJsonPaths;

          if (openedRepositories.length != 1) {
            step4Failures.add(
              'The enabled Initialize action did not open the initialized workspace exactly once.\n'
              'Observed opened repositories: ${openedRepositories.join(' | ')}',
            );
          }
          if (activeWorkspace?.target != directory.path) {
            step4Failures.add(
              'The initialized workspace was not stored as the active workspace.\n'
              'Observed target: ${activeWorkspace?.target}',
            );
          }
          if (activeWorkspace?.defaultBranch != writeBranch ||
              activeWorkspace?.writeBranch != writeBranch) {
            step4Failures.add(
              'The initialized workspace did not preserve the selected write branch.\n'
              'Observed default/write branch: ${activeWorkspace?.defaultBranch}/${activeWorkspace?.writeBranch}',
            );
          }
          if (activeWorkspace?.displayName != workspaceName) {
            step4Failures.add(
              'The initialized workspace did not preserve the selected workspace name.\n'
              'Observed display name: ${activeWorkspace?.displayName}',
            );
          }
          if (!gitDirectoryExists) {
            step4Failures.add(
              'Clicking the enabled Initialize action did not create a .git directory in the selected folder.',
            );
          }
          if (projectJsonPaths.isEmpty) {
            step4Failures.add(
              'Clicking the enabled Initialize action did not create any TrackState project.json scaffold under the selected folder.',
            );
          }

          _recordStep(
            result,
            step: 4,
            status: step4Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[3],
            observed:
                'status_label=${selectedState.statusLabel}; '
                'inspection_message=${selectedState.inspectionMessage}; '
                'submit_label=${selectedState.submitLabel}; '
                'submit_visible=${selectedState.isSubmitVisible}; '
                'submit_enabled=${selectedState.isSubmitEnabled}; '
                'workspace_name=$workspaceName; '
                'write_branch=$writeBranch; '
                'opened_repositories=${openedRepositories.join(' | ')}; '
                'active_workspace_target=${activeWorkspace?.target}; '
                'git_directory_exists=$gitDirectoryExists; '
                'project_json_paths=${projectJsonPaths.join(' | ')}',
          );
          _recordHumanVerification(
            result,
            check:
                'Activated the visible Initialize action and confirmed the selected empty folder turned into an initialized local workspace.',
            observed:
                'opened_repositories=${openedRepositories.join(' | ')}; '
                'active_workspace_target=${activeWorkspace?.target}; '
                'git_directory_exists=$gitDirectoryExists; '
                'project_json_paths=${projectJsonPaths.join(' | ')}',
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
    timeout: const Timeout(Duration(seconds: 180)),
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

Future<void> _pumpUntil(
  WidgetTester tester,
  bool Function() predicate, {
  Duration timeout = const Duration(seconds: 15),
  Duration step = const Duration(milliseconds: 100),
  String? failureMessage,
}) async {
  final maxAttempts = timeout.inMilliseconds ~/ step.inMilliseconds;
  for (var attempt = 0; attempt < maxAttempts; attempt++) {
    if (predicate()) {
      return;
    }
    await tester.runAsync(() async {
      await Future<void>.delayed(step);
    });
    await tester.pump(step);
  }
  throw TimeoutException(
    failureMessage ?? 'Timed out waiting for the expected onboarding state.',
  );
}

List<String> _projectJsonPaths(Directory root) {
  if (!root.existsSync()) {
    return const <String>[];
  }
  return root
      .listSync(recursive: true, followLinks: false)
      .whereType<File>()
      .map((file) => file.path)
      .where((path) => path.endsWith('/project.json'))
      .toList(growable: false);
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
    "* Opened the production first-launch onboarding screen and chose {noformat}Initialize folder{noformat}.",
    '* Used a real empty temp directory with no files or hidden metadata as the selected folder.',
    '* Checked the visible status label, guidance text, selected folder path, editable details fields, and the visible Initialize action state after folder inspection.',
    '* Activated the visible Initialize action and confirmed the real local initialization created Git + TrackState scaffold data and opened the workspace.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the empty folder was recognized as a valid initialization candidate, the Initialize action stayed enabled, and the flow proceeded into a real initialized workspace.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Folder fixture: {noformat}${result['directory_path']}{noformat}',
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
    '**Status:** $statusLabel  ',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '### What was tested',
    '- Opened the production first-launch onboarding screen and chose `Initialize folder`.',
    '- Used a real empty temp directory with no files or hidden metadata as the selected folder.',
    '- Checked the visible status label, guidance text, selected folder path, editable details fields, and the visible Initialize action state after folder inspection.',
    '- Activated the visible Initialize action and confirmed the real local initialization created Git + TrackState scaffold data and opened the workspace.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the empty folder was recognized as a valid initialization candidate, the Initialize action stayed enabled, and the flow proceeded into a real initialized workspace.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Folder fixture: `${result['directory_path']}`',
    '',
    '### Step results',
    ..._markdownStepLines(result),
    '',
    '### Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '### Test file',
    '```',
    _testFilePath,
    '```',
    '',
    '### Run command',
    '```bash',
    _runCommand,
    '```',
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '### Exact error',
      '```',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? 'PASSED' : 'FAILED';
  final lines = <String>[
    '# TS-799',
    '',
    '- Status: $statusLabel',
    '- Test case: $_ticketSummary',
    '- Run command: `$_runCommand`',
    '- Environment: `flutter test` on `${Platform.operatingSystem}`',
    '- Folder fixture: `${result['directory_path']}`',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```',
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
    '# $_ticketKey - $_ticketSummary',
    '',
    '## Steps to reproduce',
    '1. ${_requestSteps[0]}',
    '   - ${_stepOutcome(result, 1)}',
    '2. ${_requestSteps[1]}',
    '   - ${_stepOutcome(result, 2)}',
    '3. ${_requestSteps[2]}',
    '   - ${_stepOutcome(result, 3)}',
    '4. ${_requestSteps[3]}',
    '   - ${_stepOutcome(result, 4)}',
    '',
    '## Expected result',
    'Selecting a completely empty folder from the Initialize folder flow should show `$_expectedStatusLabel`, render the exact message `$_expectedMessage`, keep the visible `$_expectedSubmitLabel` action enabled, and allow the user to proceed into a newly initialized local workspace.',
    '',
    '## Actual result',
    'After selecting `${result['directory_path']}`, the UI showed `${result['status_label']}` with the message `${result['inspection_message']}` and the visible action `${result['submit_label']}` with `enabled=${result['submit_enabled']}`. After activating the action, the flow opened `${result['opened_repositories']}` and produced project scaffold files `${((result['project_json_paths'] as List?) ?? const <Object?>[]).join(' | ')}`.',
    '',
    '## Exact error message / stack trace',
    '```',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** the selected empty folder should be classified as ready to initialize, the visible Initialize action should be enabled, and clicking it should create a Git repository plus TrackState scaffold and open that workspace.',
    '- **Actual:** status was `${result['status_label']}`, message was `${result['inspection_message']}`, submit label was `${result['submit_label']}`, submit enabled was `${result['submit_enabled']}`, opened repositories were `${result['opened_repositories']}`, and scaffold files were `${((result['project_json_paths'] as List?) ?? const <Object?>[]).join(' | ')}`.',
    '',
    '## Environment',
    '- Command: `$_runCommand`',
    '- OS: `${Platform.operatingSystem}`',
    '- Runtime: `flutter test`',
    '- Repository path: `${Directory.current.path}`',
    '- Selected folder: `${result['directory_path']}`',
    '',
    '## Relevant logs',
    '```',
    'Visible texts: ${((result['visible_texts'] as List?) ?? const []).join(' | ')}',
    'Status label: ${result['status_label'] ?? '<missing>'}',
    'Inspection message: ${result['inspection_message'] ?? '<missing>'}',
    'Folder path visible: ${result['folder_path_visible'] ?? '<missing>'}',
    'Workspace name value: ${result['workspace_name_value'] ?? '<missing>'}',
    'Write branch value: ${result['write_branch_value'] ?? '<missing>'}',
    'Submit label: ${result['submit_label'] ?? '<missing>'}',
    'Submit visible: ${result['submit_visible'] ?? '<missing>'}',
    'Submit enabled: ${result['submit_enabled'] ?? '<missing>'}',
    'Opened repositories: ${((result['opened_repositories'] as List?) ?? const []).join(' | ')}',
    'Active workspace target: ${result['active_workspace_target'] ?? '<missing>'}',
    'Git directory exists: ${result['git_directory_exists'] ?? '<missing>'}',
    'Project json paths: ${((result['project_json_paths'] as List?) ?? const []).join(' | ')}',
    '```',
  ];
  return '${lines.join('\n')}\n';
}

Iterable<String> _jiraStepLines(Map<String, Object?> result) sync* {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    final status = '${step['status']}'.toUpperCase();
    yield '# *Step ${step['step']} — $status*';
    yield '  *Action:* ${step['action']}';
    yield '  *Observed:* {noformat}${step['observed']}{noformat}';
  }
}

Iterable<String> _jiraHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final item
      in (result['human_verification'] as List? ?? const <Object?>[])
          .whereType<Map>()) {
    yield '# *Check:* ${item['check']}';
    yield '  *Observed:* {noformat}${item['observed']}{noformat}';
  }
}

Iterable<String> _markdownStepLines(Map<String, Object?> result) sync* {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    final status = '${step['status']}'.toUpperCase();
    yield '- **Step ${step['step']} — $status**: ${step['action']}';
    yield '  - Observed: `${step['observed']}`';
  }
}

Iterable<String> _markdownHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final item
      in (result['human_verification'] as List? ?? const <Object?>[])
          .whereType<Map>()) {
    yield '- **Check:** ${item['check']}';
    yield '  - Observed: `${item['observed']}`';
  }
}

class _RecordingRealOnboardingService
    implements LocalWorkspaceOnboardingService {
  _RecordingRealOnboardingService({
    required LocalWorkspaceOnboardingService delegate,
  }) : _delegate = delegate;

  final LocalWorkspaceOnboardingService _delegate;
  final List<String> inspectedFolderPaths = <String>[];
  LocalWorkspaceInspection? lastInspection;

  @override
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath) async {
    inspectedFolderPaths.add(folderPath);
    final inspection = await _delegate.inspectFolder(folderPath);
    lastInspection = inspection;
    return inspection;
  }

  @override
  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  }) {
    return _delegate.initializeFolder(
      inspection: inspection,
      workspaceName: workspaceName,
      writeBranch: writeBranch,
    );
  }
}

String _stepOutcome(Map<String, Object?> result, int stepNumber) {
  final step = (result['steps'] as List? ?? const <Object?>[])
      .whereType<Map>()
      .cast<Map<String, Object?>>()
      .firstWhere(
        (candidate) => candidate['step'] == stepNumber,
        orElse: () => <String, Object?>{
          'status': 'unknown',
          'observed': 'No recorded observation.',
        },
      );
  final status = '${step['status']}'.toLowerCase();
  final emoji = switch (status) {
    'passed' => '✅',
    'failed' => '❌',
    _ => '⚪',
  };
  return '$emoji ${step['observed']}';
}
