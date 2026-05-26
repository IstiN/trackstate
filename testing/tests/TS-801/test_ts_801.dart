import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service_io.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../fixtures/local_workspace_onboarding_screen_fixture.dart';

const String _ticketKey = 'TS-801';
const String _ticketSummary =
    'Initialize folder containing only hidden non-Git files — initialization blocked';
const String _testFilePath = 'testing/tests/TS-801/test_ts_801.dart';
const String _runCommand =
    'flutter test testing/tests/TS-801/test_ts_801.dart --reporter expanded';

const List<String> _requestSteps = <String>[
  "Select 'Initialize folder' on the onboarding screen.",
  'Pick the directory containing only hidden non-Git files.',
  'Observe the guidance message and the state of the Initialize button.',
];

const List<String> _hiddenFixtureNames = <String>['.DS_Store', '.metadata'];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-801 blocks initialization for a folder containing only hidden non-Git files',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final directory = Directory(
        '${Directory.systemTemp.path}/ts801-hidden-only-${DateTime.now().microsecondsSinceEpoch}',
      )..createSync(recursive: true);
      addTearDown(() {
        if (directory.existsSync()) {
          directory.deleteSync(recursive: true);
        }
      });

      final seedFiles = <String>[];
      for (final hiddenName in _hiddenFixtureNames) {
        final file = File('${directory.path}/$hiddenName');
        file.writeAsStringSync('TS-801 hidden fixture: $hiddenName\n');
        seedFiles.add(file.path);
      }
      result['directory_path'] = directory.path;
      result['directory_seed_files'] = seedFiles;
      result['directory_entries'] = directory
          .listSync()
          .map((entity) => entity.path)
          .toList();

      final onboardingService = _RecordingRealOnboardingService(
        delegate: const LocalGitWorkspaceOnboardingService(),
      );

      try {
        final screen =
            await launchLocalWorkspaceOnboardingFixture(
              tester,
              workspaceProfileService: SharedPreferencesWorkspaceProfileService(
                now: () => DateTime.utc(2026, 5, 17, 20, 45),
              ),
              onboardingService: onboardingService,
              directoryPicker:
                  ({
                    String? confirmButtonText,
                    String? initialDirectory,
                  }) async => directory.path,
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
          _recordStep(
            result,
            step: 1,
            status:
                initialState.isOnboardingVisible &&
                    initialState.isInitializeActionVisible
                ? 'passed'
                : 'failed',
            action: _requestSteps[0],
            observed:
                'onboarding_visible=${initialState.isOnboardingVisible}; '
                'initialize_action_visible=${initialState.isInitializeActionVisible}; '
                'visible_texts=${initialState.visibleTexts.join(' | ')}',
          );
          if (!initialState.isOnboardingVisible ||
              !initialState.isInitializeActionVisible) {
            throw AssertionError(
              'Step 1 failed: the first-launch onboarding screen did not expose the expected Initialize folder action before the hidden-files folder was chosen.\n'
              'Observed visible texts: ${initialState.visibleTexts.join(' | ')}',
            );
          }

          await screen.chooseInitializeFolder().timeout(
            const Duration(seconds: 20),
            onTimeout: () => throw TimeoutException(
              'Timed out waiting for the Initialize folder flow to finish inspecting the selected hidden-files folder.',
            ),
          );

          final recordedInspection = onboardingService.lastInspection;
          final inspectedFolderPaths = onboardingService.inspectedFolderPaths;
          result['inspected_folder_paths'] = inspectedFolderPaths;
          result['production_inspection_state'] =
              recordedInspection?.state.name;
          result['production_inspection_message'] = recordedInspection?.message;
          if (recordedInspection == null) {
            throw AssertionError(
              'Step 2 failed: selecting "Initialize folder" did not invoke the real onboarding inspectFolder call.',
            );
          }

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
            step: 2,
            status:
                selectedState.folderPath == directory.path &&
                    inspectedFolderPaths.length == 1 &&
                    inspectedFolderPaths.single == directory.path
                ? 'passed'
                : 'failed',
            action: _requestSteps[1],
            observed:
                'picked_folder=${selectedState.folderPath}; '
                'expected_folder=${directory.path}; '
                'inspected_paths=${inspectedFolderPaths.join(' | ')}; '
                'inspection_state=${recordedInspection.state.name}; '
                'status_label=${selectedState.statusLabel}; '
                'visible_texts=${selectedState.visibleTexts.join(' | ')}',
          );
          if (inspectedFolderPaths.length != 1 ||
              inspectedFolderPaths.single != directory.path) {
            throw AssertionError(
              'Step 2 failed: the onboarding UI did not inspect the selected hidden-files-only directory via the real onboarding service.\n'
              'Expected inspected folder path: ${directory.path}\n'
              'Observed inspected folder paths: ${inspectedFolderPaths.join(' | ')}',
            );
          }
          if (selectedState.folderPath != directory.path) {
            throw AssertionError(
              'Step 2 failed: the onboarding flow did not reflect the selected hidden-files-only directory after using Initialize folder.\n'
              'Expected folder path: ${directory.path}\n'
              'Observed folder path: ${selectedState.folderPath}\n'
              'Observed visible texts: ${selectedState.visibleTexts.join(' | ')}',
            );
          }

          final message = selectedState.inspectionMessage ?? '';
          final hasExistingGitRepositoryGuidance = message.contains(
            'existing Git repository',
          );
          final hasEmptyFolderGuidance = message.contains('empty folder');
          final submitLabel = selectedState.submitLabel ?? '';
          final step3Failures = <String>[];

          if (!hasExistingGitRepositoryGuidance || !hasEmptyFolderGuidance) {
            step3Failures.add(
              'The user-facing message did not instruct the user to choose an existing Git repository or an empty folder. '
              'Observed message: $message',
            );
          }
          if (!selectedState.isSubmitVisible ||
              !submitLabel.contains('Initialize')) {
            step3Failures.add(
              'The expected Initialize action was not visible after selecting the hidden-files folder. '
              'Observed submit label: ${selectedState.submitLabel}',
            );
          } else if (selectedState.isSubmitEnabled) {
            step3Failures.add(
              'The Initialize action remained enabled for a folder containing only hidden non-Git files.',
            );
          }

          _recordStep(
            result,
            step: 3,
            status: step3Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[2],
            observed:
                'status_label=${selectedState.statusLabel}; '
                'inspection_message=$message; '
                'submit_label=${selectedState.submitLabel}; '
                'submit_visible=${selectedState.isSubmitVisible}; '
                'submit_enabled=${selectedState.isSubmitEnabled}; '
                'workspace_name=${selectedState.workspaceNameValue}; '
                'write_branch=${selectedState.writeBranchValue}; '
                'visible_texts=${selectedState.visibleTexts.join(' | ')}',
          );

          _recordHumanVerification(
            result,
            check:
                'Viewed the first-launch onboarding screen as a user before interacting with any workspace setup controls.',
            observed: 'visible_texts=${initialState.visibleTexts.join(' | ')}',
          );
          _recordHumanVerification(
            result,
            check:
                'Chose Initialize folder and reviewed the exact status card copy, selected folder path, visible fields, and button state shown for the hidden-files-only directory.',
            observed:
                'status_label=${selectedState.statusLabel}; '
                'inspection_message=$message; '
                'folder_path=${selectedState.folderPath}; '
                'submit_label=${selectedState.submitLabel}; '
                'submit_enabled=${selectedState.isSubmitEnabled}',
          );
          _recordHumanVerification(
            result,
            check:
                'Compared the rendered guidance and Initialize action state with the user expectation that hidden files still make the folder non-empty and should block initialization.',
            observed:
                'hidden_fixture_names=${_hiddenFixtureNames.join(' | ')}; '
                'has_existing_git_repository_guidance=$hasExistingGitRepositoryGuidance; '
                'has_empty_folder_guidance=$hasEmptyFolderGuidance; '
                'submit_enabled=${selectedState.isSubmitEnabled}',
          );

          if (step3Failures.isNotEmpty) {
            throw AssertionError(step3Failures.join('\n'));
          }

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
  final seedFiles =
      ((result['directory_seed_files'] as List?) ?? const <Object?>[]).join(
        ', ',
      );
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was tested',
    '* Opened the production first-launch onboarding screen and chose {noformat}Initialize folder{noformat}.',
    '* Used a real temp directory containing only hidden non-Git files ({noformat}${_hiddenFixtureNames.join(', ')}{noformat}) as the selected folder.',
    '* Checked the visible status label, guidance text, selected folder path, workspace details fields, and the visible Initialize action state after folder inspection.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the flow blocked initialization, showed actionable guidance that points users to an existing Git repository or an empty folder, and left the Initialize action disabled.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Folder fixture: {noformat}${result['directory_path']}{noformat}',
    '* Hidden seed files: {noformat}$seedFiles{noformat}',
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
  final seedFiles =
      ((result['directory_seed_files'] as List?) ?? const <Object?>[]).join(
        ', ',
      );
  final lines = <String>[
    '## Test Automation Result',
    '',
    '**Status:** $statusLabel  ',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '### What was tested',
    '- Opened the production first-launch onboarding screen and chose `Initialize folder`.',
    '- Used a real temp directory containing only hidden non-Git files (`${_hiddenFixtureNames.join(', ')}`) as the selected folder.',
    '- Checked the visible status label, guidance text, selected folder path, workspace details fields, and the visible Initialize action state after folder inspection.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the flow blocked initialization, showed actionable guidance that points users to an existing Git repository or an empty folder, and left the Initialize action disabled.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Folder fixture: `${result['directory_path']}`',
    '- Hidden seed files: `$seedFiles`',
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
  final seedFiles =
      ((result['directory_seed_files'] as List?) ?? const <Object?>[]).join(
        ', ',
      );
  final lines = <String>[
    '# TS-801',
    '',
    '- Status: $statusLabel',
    '- Test case: $_ticketSummary',
    '- Run command: `$_runCommand`',
    '- Environment: `flutter test` on `${Platform.operatingSystem}`',
    '- Folder fixture: `${result['directory_path']}`',
    '- Hidden seed files: `$seedFiles`',
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
  final seedFiles =
      ((result['directory_seed_files'] as List?) ?? const <Object?>[]).join(
        ', ',
      );
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
    '',
    '## Expected result',
    'Selecting a folder that contains only hidden non-Git files should still block initialization, show actionable guidance that tells the user to choose an existing Git repository or an empty folder, and keep the visible Initialize action disabled.',
    '',
    '## Actual result',
    'After selecting `${result['directory_path']}`, the UI showed `${result['status_label']}` with the message `${result['inspection_message']}`. The visible Initialize action `${result['submit_label']}` remained `${result['submit_enabled'] == true ? 'enabled' : 'disabled'}` instead of blocking the flow.',
    '',
    '## Exact error message / stack trace',
    '```',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** hidden files should still make the selected folder count as non-empty, the message should explicitly direct users to choose an existing Git repository or an empty folder, and the visible Initialize action should be disabled.',
    '- **Actual:** status was `${result['status_label']}`, the message was `${result['inspection_message']}`, and the visible Initialize action `${result['submit_label']}` had `enabled=${result['submit_enabled']}`.',
    '',
    '## Environment',
    '- Command: `$_runCommand`',
    '- OS: `${Platform.operatingSystem}`',
    '- Runtime: `flutter test`',
    '- Repository path: `${Directory.current.path}`',
    '- Selected folder: `${result['directory_path']}`',
    '- Hidden seed files: `$seedFiles`',
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

Iterable<String> _markdownStepLines(Map<String, Object?> result) sync* {
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    final icon = step['status'] == 'passed' ? '✅' : '❌';
    yield '- $icon **Step ${step['step']}** — ${step['action']}';
    yield '  - Observed: `${step['observed']}`';
  }
}

Iterable<String> _jiraHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final entry
      in (result['human_verification'] as List? ?? const <Object?>[])
          .whereType<Map>()) {
    yield '# *Check:* ${entry['check']}';
    yield '  *Observed:* {noformat}${entry['observed']}{noformat}';
  }
}

Iterable<String> _markdownHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final entry
      in (result['human_verification'] as List? ?? const <Object?>[])
          .whereType<Map>()) {
    yield '- **Check:** ${entry['check']}';
    yield '  - Observed: `${entry['observed']}`';
  }
}

String _stepOutcome(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List? ?? const <Object?>[])
      .whereType<Map>();
  for (final step in steps) {
    if (step['step'] == stepNumber) {
      final passed = step['status'] == 'passed';
      final prefix = passed ? 'Passed ✅' : 'Failed ❌';
      return '$prefix — ${step['observed']}';
    }
  }
  return 'Not executed ❌';
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
