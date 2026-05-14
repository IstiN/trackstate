import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service_io.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../fixtures/local_workspace_onboarding_screen_fixture.dart';

const String _ticketKey = 'TS-719';
const String _ticketSummary =
    'Blocked folder detection — non-empty non-Git folder feedback';
const String _testFilePath = 'testing/tests/TS-719/test_ts_719.dart';
const String _runCommand =
    'flutter test testing/tests/TS-719/test_ts_719.dart --reporter expanded';

const List<String> _requestSteps = <String>[
  "Select 'Initialize folder' on the Onboarding screen.",
  'Pick the non-empty non-git directory.',
  'Observe the error messaging and action state.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-719 blocks initialization for a non-empty non-Git folder',
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
        '${Directory.systemTemp.path}/ts719-non-git-${DateTime.now().microsecondsSinceEpoch}',
      )..createSync(recursive: true);
      addTearDown(() {
        if (directory.existsSync()) {
          directory.deleteSync(recursive: true);
        }
      });
      final seedFile = File('${directory.path}/notes.txt');
      seedFile.writeAsStringSync('TS-719 reproduction fixture\n');
      result['directory_path'] = directory.path;
      result['directory_seed_file'] = seedFile.path;
      final productionInspection = await tester.runAsync(
        () => const LocalGitWorkspaceOnboardingService().inspectFolder(
          directory.path,
        ),
      );
      if (productionInspection == null) {
        throw StateError(
          'Timed out waiting for the production folder inspection result.',
        );
      }
      result['production_inspection_state'] = productionInspection.state.name;
      result['production_inspection_message'] = productionInspection.message;

      try {
        final screen =
            await launchLocalWorkspaceOnboardingFixture(
              tester,
              workspaceProfileService: SharedPreferencesWorkspaceProfileService(
                now: () => DateTime.utc(2026, 5, 14, 15, 40),
              ),
              onboardingService: _PrecomputedInspectionOnboardingService(
                inspection: productionInspection,
              ),
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
              'Step 1 failed: the first-launch onboarding screen did not expose the expected Initialize folder action before the folder was chosen.\n'
              'Observed visible texts: ${initialState.visibleTexts.join(' | ')}',
            );
          }

          await screen.chooseInitializeFolder().timeout(
            const Duration(seconds: 20),
            onTimeout: () => throw TimeoutException(
              'Timed out waiting for the Initialize folder flow to finish inspecting the selected folder.',
            ),
          );
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
            status: selectedState.folderPath == directory.path
                ? 'passed'
                : 'failed',
            action: _requestSteps[1],
            observed:
                'picked_folder=${selectedState.folderPath}; '
                'expected_folder=${directory.path}; '
                'status_label=${selectedState.statusLabel}; '
                'visible_texts=${selectedState.visibleTexts.join(' | ')}',
          );
          if (selectedState.folderPath != directory.path) {
            throw AssertionError(
              'Step 2 failed: the onboarding flow did not reflect the selected non-empty non-Git directory after using Initialize folder.\n'
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

          if (selectedState.statusLabel != 'Folder not supported') {
            step3Failures.add(
              'The onboarding flow was not blocked after selecting a non-empty non-Git folder. '
              'Observed status label: ${selectedState.statusLabel}',
            );
          }
          if (!hasExistingGitRepositoryGuidance || !hasEmptyFolderGuidance) {
            step3Failures.add(
              'The user-facing message did not instruct the user to choose an existing Git repository or an empty folder. '
              'Observed message: $message',
            );
          }
          if (!selectedState.isSubmitVisible ||
              !submitLabel.contains('Initialize')) {
            step3Failures.add(
              'The expected Initialize action was not visible after selecting the folder. '
              'Observed submit label: ${selectedState.submitLabel}',
            );
          } else if (selectedState.isSubmitEnabled) {
            step3Failures.add(
              'The Initialize action remained enabled for a non-empty non-Git folder.',
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
                'Chose Initialize folder and reviewed the exact status card copy, selected folder path, visible fields, and button state shown for the non-empty non-Git directory.',
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
                'Compared the rendered message and Initialize action state with the user expectation that this flow should be blocked and should direct users to an existing Git repository or an empty folder.',
            observed:
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
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was tested',
    "* Opened the production first-launch onboarding screen and chose {noformat}Initialize folder{noformat}.",
    '* Used a real non-empty non-Git temp directory containing {noformat}notes.txt{noformat} as the selected folder.',
    '* Checked the visible status label, guidance text, selected folder path, workspace details fields, and the visible Initialize action state after folder inspection.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the flow blocked initialization, showed actionable guidance that points users to an existing Git repository or an empty folder, and left the Initialize action disabled.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Folder fixture: {noformat}${result['directory_path']}{noformat}',
    '* Seed file: {noformat}${result['directory_seed_file']}{noformat}',
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
    '- Used a real non-empty non-Git temp directory containing `notes.txt` as the selected folder.',
    '- Checked the visible status label, guidance text, selected folder path, workspace details fields, and the visible Initialize action state after folder inspection.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the flow blocked initialization, showed actionable guidance that points users to an existing Git repository or an empty folder, and left the Initialize action disabled.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Folder fixture: `${result['directory_path']}`',
    '- Seed file: `${result['directory_seed_file']}`',
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
    '# TS-719',
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
    '',
    '## Expected result',
    'Selecting a non-empty non-Git folder from the Initialize folder flow should block initialization, show actionable guidance that tells the user to choose an existing Git repository or an empty folder, and keep the visible Initialize action disabled.',
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
    '- **Expected:** status should reflect a blocked folder, the message should explicitly direct users to choose an existing Git repository or an empty folder, and the visible Initialize action should be disabled.',
    '- **Actual:** status was `${result['status_label']}`, the message was `${result['inspection_message']}`, and the visible Initialize action `${result['submit_label']}` had `enabled=${result['submit_enabled']}`.',
    '',
    '## Environment',
    '- Command: `$_runCommand`',
    '- OS: `${Platform.operatingSystem}`',
    '- Runtime: `flutter test`',
    '- Repository path: `${Directory.current.path}`',
    '- Selected folder: `${result['directory_path']}`',
    '- Seed file: `${result['directory_seed_file']}`',
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

class _PrecomputedInspectionOnboardingService
    implements LocalWorkspaceOnboardingService {
  const _PrecomputedInspectionOnboardingService({required this.inspection});

  final LocalWorkspaceInspection inspection;

  @override
  Future<LocalWorkspaceInspection> inspectFolder(String folderPath) async {
    return inspection;
  }

  @override
  Future<LocalWorkspaceSetupResult> initializeFolder({
    required LocalWorkspaceInspection inspection,
    required String workspaceName,
    required String writeBranch,
  }) {
    throw UnimplementedError(
      'TS-719 should fail before initialization is attempted.',
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
