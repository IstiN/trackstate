import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service_io.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../fixtures/workspace_onboarding_screen_fixture.dart';
import 'support/ts800_existing_git_repository_fixture.dart';

const String _ticketKey = 'TS-800';
const String _ticketSummary =
    'Select an existing Git repository — folder recognized and initialization skipped';
const String _testFilePath = 'testing/tests/TS-800/test_ts_800.dart';
const String _runCommand =
    'flutter test testing/tests/TS-800/test_ts_800.dart --reporter expanded';
const String _readyStatus = 'Ready to open';
const String _readyMessage =
    'This folder is an existing committed Git repository and can be opened in TrackState without initialization.';
const String _openExistingFolderLabel = 'Open existing folder';
const String _openWorkspaceLabel = 'Open workspace';
const String _initializeHereLabel = 'Initialize TrackState here';
const List<String> _requestSteps = <String>[
  'Open the first-launch onboarding screen.',
  'Select the option to pick a folder/initialize.',
  'Select the directory that already contains the .git folder.',
  'Observe the UI feedback.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-800 recognizes an existing Git repository and skips re-initialization',
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

      final semantics = tester.ensureSemantics();
      final fixture = await tester.runAsync(
        Ts800ExistingGitRepositoryFixture.create,
      );
      if (fixture == null) {
        semantics.dispose();
        throw StateError('TS-800 fixture creation did not complete.');
      }
      addTearDown(() async {
        await tester.runAsync(fixture.dispose);
      });

      try {
        final service = const LocalGitWorkspaceOnboardingService();
        final beforeSnapshot = await tester.runAsync(fixture.captureSnapshot);
        if (beforeSnapshot == null) {
          throw StateError(
            'TS-800 pre-open repository snapshot did not complete.',
          );
        }

        result['repository_path'] = fixture.repositoryPath;
        result['workspace_folder_name'] = fixture.repositoryFolderName;
        result['before_head_revision'] = beforeSnapshot.headRevision;
        result['before_worktree_status'] = beforeSnapshot.worktreeStatusLines;
        result['before_files'] = beforeSnapshot.files;

        final inspection = await tester.runAsync(
          () => service.inspectFolder(fixture.repositoryPath),
        );
        if (inspection == null) {
          throw StateError('TS-800 inspection did not complete.');
        }

        result['inspection'] = <String, Object?>{
          'state': inspection.state.name,
          'message': inspection.message,
          'folderPath': inspection.folderPath,
          'suggestedWorkspaceName': inspection.suggestedWorkspaceName,
          'suggestedWriteBranch': inspection.suggestedWriteBranch,
          'detectedWriteBranch': inspection.detectedWriteBranch,
          'hasGitRepository': inspection.hasGitRepository,
          'canOpen': inspection.canOpen,
        };

        if (inspection.state == LocalWorkspaceInspectionState.blocked ||
            inspection.folderPath != fixture.repositoryPath ||
            !inspection.hasGitRepository) {
          throw AssertionError(
            'Precondition failed: the production LocalWorkspaceOnboardingService did not recognize the prepared folder as an existing Git repository.\n'
            'Observed state: ${inspection.state.name}\n'
            'Observed message: ${inspection.message}\n'
            'Observed folder path: ${inspection.folderPath}\n'
            'Observed hasGitRepository: ${inspection.hasGitRepository}\n'
            'Observed canOpen: ${inspection.canOpen}\n'
            'Observed canInitialize: ${inspection.canInitialize}',
          );
        }

        final pickerInvocations = <Map<String, String?>>[];
        final openedRepositories = <String>[];
        final onboardingService = _RecordingRealOnboardingService(
          delegate: service,
        );
        final workspaceProfileService =
            SharedPreferencesWorkspaceProfileService(
              now: () => DateTime.utc(2026, 5, 17, 20, 29),
            );

        final screen = await launchWorkspaceOnboardingFixture(
          tester,
          workspaceProfileService: workspaceProfileService,
          localWorkspaceOnboardingService: onboardingService,
          workspaceDirectoryPicker:
              ({String? confirmButtonText, String? initialDirectory}) async {
                pickerInvocations.add(<String, String?>{
                  'confirmButtonText': confirmButtonText,
                  'initialDirectory': initialDirectory,
                });
                return fixture.repositoryPath;
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
        );

        try {
          final initialState = screen.captureState();
          final initialVisibleTexts = initialState.visibleTexts;
          result['initial_visible_texts'] = initialVisibleTexts;
          final step1Passed =
              initialState.isOnboardingVisible &&
              initialVisibleTexts.contains('Add workspace') &&
              initialVisibleTexts.contains(_openExistingFolderLabel);
          _recordStep(
            result,
            step: 1,
            status: step1Passed ? 'passed' : 'failed',
            action: _requestSteps[0],
            observed:
                'onboarding_visible=${initialState.isOnboardingVisible}; visible_texts=${_formatList(initialVisibleTexts)}',
          );
          if (!step1Passed) {
            throw AssertionError(
              'Step 1 failed: the first-launch onboarding screen did not render the expected local folder entry point.\n'
              'Observed visible texts: ${_formatList(initialVisibleTexts)}',
            );
          }

          await screen.chooseExistingFolder();

          final recordedInspection = onboardingService.lastInspection;
          final pickerInvocation = _singleOrNullMap(pickerInvocations);
          final step2Passed =
              pickerInvocation != null &&
              pickerInvocation['confirmButtonText'] ==
                  'Choose existing folder' &&
              recordedInspection != null;
          result['picker_invocation'] = pickerInvocation;
          result['production_inspection'] = recordedInspection == null
              ? null
              : <String, Object?>{
                  'state': recordedInspection.state.name,
                  'message': recordedInspection.message,
                  'folderPath': recordedInspection.folderPath,
                  'suggestedWorkspaceName':
                      recordedInspection.suggestedWorkspaceName,
                  'suggestedWriteBranch':
                      recordedInspection.suggestedWriteBranch,
                  'detectedWriteBranch': recordedInspection.detectedWriteBranch,
                  'hasGitRepository': recordedInspection.hasGitRepository,
                  'canOpen': recordedInspection.canOpen,
                };
          _recordStep(
            result,
            step: 2,
            status: step2Passed ? 'passed' : 'failed',
            action: _requestSteps[1],
            observed:
                'picker_invocations=${jsonEncode(pickerInvocations)}; inspected_folder_paths=${_formatList(onboardingService.inspectedFolderPaths)}; production_inspection_state=${recordedInspection?.state.name ?? '<missing>'}',
          );
          if (!step2Passed) {
            throw AssertionError(
              'Step 2 failed: selecting the local folder flow did not invoke the real onboarding inspection through the expected existing-folder picker action.\n'
              'Observed picker invocations: ${jsonEncode(pickerInvocations)}\n'
              'Observed recorded inspection: ${recordedInspection == null ? '<missing>' : recordedInspection.state.name}',
            );
          }
          final productionInspection = recordedInspection;

          final selectedState = screen.captureState();
          final visibleTexts = selectedState.visibleTexts;
          final interactiveLabels = selectedState.interactiveSemanticsLabels;
          result['inspection_paths'] = onboardingService.inspectedFolderPaths;
          result['visible_texts'] = visibleTexts;
          result['interactive_semantics_labels'] = interactiveLabels;
          result['local_folder_path'] = selectedState.localFolderPath;
          result['primary_action_label'] = selectedState.primaryActionLabel;
          result['primary_action_enabled'] =
              selectedState.isPrimaryActionEnabled;
          result['local_workspace_name_value'] =
              selectedState.localWorkspaceNameValue;
          result['local_write_branch_value'] =
              selectedState.localWriteBranchValue;
          result['status_label'] = visibleTexts.contains(_readyStatus)
              ? _readyStatus
              : null;
          result['inspection_message'] = visibleTexts.contains(_readyMessage)
              ? _readyMessage
              : null;

          final step3Passed =
              onboardingService.inspectedFolderPaths.length == 1 &&
              onboardingService.inspectedFolderPaths.single ==
                  fixture.repositoryPath &&
              productionInspection.state !=
                  LocalWorkspaceInspectionState.blocked &&
              productionInspection.folderPath == fixture.repositoryPath &&
              productionInspection.hasGitRepository &&
              selectedState.localFolderPath == fixture.repositoryPath;
          _recordStep(
            result,
            step: 3,
            status: step3Passed ? 'passed' : 'failed',
            action: _requestSteps[2],
            observed:
                'selected_folder=${selectedState.localFolderPath}; expected_folder=${fixture.repositoryPath}; inspected_folder_paths=${_formatList(onboardingService.inspectedFolderPaths)}; production_inspection_state=${productionInspection.state.name}',
          );
          if (!step3Passed) {
            throw AssertionError(
              'Step 3 failed: the onboarding flow did not keep the selected existing Git repository visible after folder selection.\n'
              'Expected folder path: ${fixture.repositoryPath}\n'
              'Observed folder path: ${selectedState.localFolderPath}\n'
              'Observed inspected folder paths: ${_formatList(onboardingService.inspectedFolderPaths)}\n'
              'Observed recorded inspection state: ${productionInspection.state.name}\n'
              'Observed recorded inspection folder path: ${productionInspection.folderPath}\n'
              'Observed recorded hasGitRepository: ${productionInspection.hasGitRepository}\n'
              'Observed recorded canOpen: ${productionInspection.canOpen}\n'
              'Observed recorded canInitialize: ${productionInspection.canInitialize}',
            );
          }

          final missingTexts =
              <String>[
                    _readyStatus,
                    _readyMessage,
                    'Selected folder',
                    fixture.repositoryPath,
                    'Workspace details',
                    'Workspace name',
                    'Write Branch',
                    _openWorkspaceLabel,
                  ]
                  .where((text) => !visibleTexts.contains(text))
                  .toList(growable: false);
          final step4Failures = <String>[];
          if (missingTexts.isNotEmpty) {
            step4Failures.add(
              'The ready-state feedback was missing: ${_formatList(missingTexts)}.',
            );
          }
          if (selectedState.primaryActionLabel != _openWorkspaceLabel) {
            step4Failures.add(
              'The primary action did not switch to `$_openWorkspaceLabel`. Observed: ${selectedState.primaryActionLabel}',
            );
          }
          if (!selectedState.isPrimaryActionEnabled) {
            step4Failures.add(
              'The ready-state primary action was disabled, so the user was blocked from continuing.',
            );
          }
          if (selectedState.primaryActionLabel == _initializeHereLabel) {
            step4Failures.add(
              'The UI still exposed the initialization CTA instead of skipping re-initialization.',
            );
          }
          _recordStep(
            result,
            step: 4,
            status: step4Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[3],
            observed:
                'status_label=${result['status_label'] ?? '<missing>'}; inspection_message=${result['inspection_message'] ?? '<missing>'}; primary_action=${selectedState.primaryActionLabel}; primary_action_enabled=${selectedState.isPrimaryActionEnabled}; workspace_name=${selectedState.localWorkspaceNameValue}; write_branch=${selectedState.localWriteBranchValue}; visible_texts=${_formatList(visibleTexts)}',
          );
          if (step4Failures.isNotEmpty) {
            throw AssertionError(step4Failures.join('\n'));
          }

          await screen.submit();

          final afterSnapshot = await tester.runAsync(fixture.captureSnapshot);
          if (afterSnapshot == null) {
            throw StateError(
              'TS-800 post-open repository snapshot did not complete.',
            );
          }
          final postOpenState = screen.captureState();
          result['after_head_revision'] = afterSnapshot.headRevision;
          result['after_worktree_status'] = afterSnapshot.worktreeStatusLines;
          result['after_files'] = afterSnapshot.files;
          result['opened_repositories'] = openedRepositories;
          result['dashboard_visible'] = postOpenState.isDashboardVisible;

          if (_singleOrNull(openedRepositories) !=
                  '${fixture.repositoryPath}@main@main' ||
              afterSnapshot.headRevision != beforeSnapshot.headRevision ||
              !_listEquals(
                afterSnapshot.worktreeStatusLines,
                beforeSnapshot.worktreeStatusLines,
              ) ||
              !_mapEquals(afterSnapshot.files, beforeSnapshot.files) ||
              !postOpenState.isDashboardVisible) {
            throw AssertionError(
              'Continuation check failed: the user-facing Open workspace action did not complete cleanly for the selected existing Git repository.\n'
              'Observed opened repositories: ${_formatList(openedRepositories)}\n'
              'Observed head revision before/after: ${beforeSnapshot.headRevision} -> ${afterSnapshot.headRevision}\n'
              'Observed worktree status before: ${_formatList(beforeSnapshot.worktreeStatusLines)}\n'
              'Observed worktree status after: ${_formatList(afterSnapshot.worktreeStatusLines)}\n'
              'Observed dashboard visible: ${postOpenState.isDashboardVisible}',
            );
          }

          _recordHumanVerification(
            result,
            check:
                'Viewed the onboarding state a user sees after selecting an existing Git repository, including the ready status, selected folder path, workspace details labels, and the primary CTA text.',
            observed:
                'visible_texts=${_formatList(visibleTexts)}; interactive_semantics_labels=${_formatList(interactiveLabels)}',
          );
          _recordHumanVerification(
            result,
            check:
                'Used the visible Open workspace action and confirmed the dashboard opened without triggering re-initialization or mutating the selected repository on disk.',
            observed:
                'dashboard_visible=${postOpenState.isDashboardVisible}; opened_repositories=${_formatList(openedRepositories)}; head_revision=${afterSnapshot.headRevision}; worktree_status=${_formatList(afterSnapshot.worktreeStatusLines)}; file_manifest_unchanged=${_mapEquals(afterSnapshot.files, beforeSnapshot.files)}',
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
        semantics.dispose();
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
    '* Opened the production first-launch onboarding screen and used the local folder picker flow for an existing Git repository.',
    '* Selected a real committed local Git repository containing a {.git} directory but no existing TrackState workspace metadata.',
    '* Checked the ready-state status text, guidance message, selected folder path, workspace details fields, and the visible primary action to confirm initialization was skipped.',
    '* Activated the visible {noformat}Open workspace{noformat} action to confirm the user could continue.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the folder was recognized as an existing Git repository, the onboarding UI skipped re-initialization by surfacing {noformat}Open workspace{noformat}, and the user could continue into the dashboard.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository fixture: {noformat}${result['repository_path']}{noformat}',
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
    '- Opened the production first-launch onboarding screen and used the local folder picker flow for an existing Git repository.',
    '- Selected a real committed local Git repository containing a `.git` directory but no existing TrackState workspace metadata.',
    '- Checked the ready-state status text, guidance message, selected folder path, workspace details fields, and the visible primary action to confirm initialization was skipped.',
    '- Activated the visible `Open workspace` action to confirm the user could continue.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the folder was recognized as an existing Git repository, the onboarding UI skipped re-initialization by surfacing `Open workspace`, and the user could continue into the dashboard.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Repository fixture: `${result['repository_path']}`',
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
    '# TS-800',
    '',
    '- Status: $statusLabel',
    '- Test case: $_ticketSummary',
    '- Run command: `$_runCommand`',
    '- Environment: `flutter test` on `${Platform.operatingSystem}`',
    '- Repository fixture: `${result['repository_path']}`',
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
    'The onboarding UI should recognize the selected folder as an existing Git repository, skip re-initialization by replacing the initialization path with an enabled `Open workspace` action, and allow the user to continue.',
    '',
    '## Actual result',
    'After selecting `${result['repository_path']}`, the production inspection reported `${(result['production_inspection'] as Map?)?['state'] ?? '<missing>'}` and the UI showed status `${result['status_label'] ?? '<missing>'}` with message `${result['inspection_message'] ?? '<missing>'}` and primary action `${result['primary_action_label'] ?? '<missing>'}` (`enabled=${result['primary_action_enabled']}`). Dashboard visible after continuing: `${result['dashboard_visible'] ?? '<missing>'}`.',
    '',
    '## Exact error message / stack trace',
    '```',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** selecting an existing Git repository should show ready-to-open feedback, avoid a re-initialization CTA, and allow the user to continue with `Open workspace`.',
    '- **Actual:** the real onboarding inspection for the plain Git repository returned `${(result['production_inspection'] as Map?)?['state'] ?? '<missing>'}`, visible texts were `${_formatList((result['visible_texts'] as List?)?.cast<Object?>() ?? const <Object?>[])}`, and the primary action was `${result['primary_action_label'] ?? '<missing>'}` with `enabled=${result['primary_action_enabled']}`.',
    '',
    '## Environment',
    '- Command: `$_runCommand`',
    '- OS: `${Platform.operatingSystem}`',
    '- Runtime: `flutter test`',
    '- Repository path: `${Directory.current.path}`',
    '- Selected folder: `${result['repository_path']}`',
    '',
    '## Relevant logs',
    '```',
    'Picker invocation: ${jsonEncode(result['picker_invocation'])}',
    'Production inspection: ${jsonEncode(result['production_inspection'])}',
    'Inspected folder paths: ${_inspectionPaths(result)}',
    'Visible texts: ${_formatList((result['visible_texts'] as List?)?.cast<Object?>() ?? const <Object?>[])}',
    'Interactive semantics labels: ${_formatList((result['interactive_semantics_labels'] as List?)?.cast<Object?>() ?? const <Object?>[])}',
    'Primary action label: ${result['primary_action_label'] ?? '<missing>'}',
    'Primary action enabled: ${result['primary_action_enabled'] ?? '<missing>'}',
    'Dashboard visible: ${result['dashboard_visible'] ?? '<missing>'}',
    'Opened repositories: ${_formatList((result['opened_repositories'] as List?)?.cast<Object?>() ?? const <Object?>[])}',
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

String? _singleOrNull(List<String> values) {
  if (values.length != 1) {
    return null;
  }
  return values.single;
}

Map<String, String?>? _singleOrNullMap(List<Map<String, String?>> values) {
  if (values.length != 1) {
    return null;
  }
  return values.single;
}

String _formatList(List<Object?> values) {
  if (values.isEmpty) {
    return '<empty>';
  }
  return values.map((value) => value.toString()).join(' | ');
}

bool _listEquals(List<String> left, List<String> right) {
  if (left.length != right.length) {
    return false;
  }
  for (var index = 0; index < left.length; index += 1) {
    if (left[index] != right[index]) {
      return false;
    }
  }
  return true;
}

bool _mapEquals(Map<String, String> left, Map<String, String> right) {
  if (left.length != right.length) {
    return false;
  }
  for (final entry in left.entries) {
    if (right[entry.key] != entry.value) {
      return false;
    }
  }
  return true;
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

String _inspectionPaths(Map<String, Object?> result) {
  final inspectionPaths = result['inspection_paths'];
  if (inspectionPaths is List) {
    return _formatList(inspectionPaths.cast<Object?>());
  }
  return '<missing>';
}
