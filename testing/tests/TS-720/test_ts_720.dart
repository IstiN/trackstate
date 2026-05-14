import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/local_workspace_onboarding_service.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/settings_screen_robot.dart';
import '../../core/utils/color_contrast.dart';

const String _ticketKey = 'TS-720';
const String _ticketSummary =
    'Workspace details defaulting — folder name as display name proposal';
const String _testFilePath = 'testing/tests/TS-720/test_ts_720.dart';
const String _runCommand =
    'flutter test testing/tests/TS-720/test_ts_720.dart --reporter expanded';
const String _expectedFolderName = 'alpha-project';
const String _expectedBranch = 'master';
const String _editedWorkspaceName = 'Alpha Project QA';
const String _editedWriteBranch = 'master-hotfix';
const String _workspaceDetailsHeading = 'Workspace details';
const String _workspaceNameLabel = 'Workspace name';
const String _writeBranchLabel = 'Write Branch';
const String _changeFolderLabel = 'Change folder';
const String _submitLabel = 'Initialize TrackState here';
const String _statusLabel = 'Initialization required';
const String _selectedFolderLabel = 'Selected folder';
const String _workspaceNameHelper =
    'Defaults to the selected folder name. You can rename it before saving the workspace profile.';
const String _writeBranchHelper =
    'TrackState opens and writes to this local branch. Existing repositories must stay on their current branch during onboarding.';
const String _statusMessage =
    'Git is already initialized here, but TrackState metadata is missing. Initialize TrackState here to create the project scaffold.';

const List<String> _requestSteps = <String>[
  "Select 'Open existing folder' and pick the 'alpha-project' directory.",
  'Navigate to the Workspace Details step.',
  "Verify the prefilled values for 'Display Name' and 'Write Branch'.",
  'Attempt to edit both fields.',
  'Verify keyboard focus order is logical and contrast is AA compliant (AC6).',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-720 workspace details propose folder name and detected master branch',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test widget harness',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };
      final robot = SettingsScreenRobot(tester);
      final semantics = tester.ensureSemantics();
      _PreparedWorkspace? preparedWorkspace;

      try {
        preparedWorkspace = await tester.runAsync<_PreparedWorkspace>(
          _prepareReadyWorkspace,
        );
        if (preparedWorkspace == null) {
          throw StateError('The TS-720 test workspace could not be prepared.');
        }

        result['workspace_path'] = preparedWorkspace.repositoryPath;
        result['precondition_inspection_state'] = preparedWorkspace.stateName;
        result['precondition_suggested_workspace_name'] =
            preparedWorkspace.suggestedWorkspaceName;
        result['precondition_suggested_write_branch'] =
            preparedWorkspace.suggestedWriteBranch;
        result['precondition_detected_branch'] =
            preparedWorkspace.detectedWriteBranch;

        if (!preparedWorkspace.canContinueOnboarding) {
          throw AssertionError(
            'Precondition failed: the prepared alpha-project repository did not reach the production initialize-ready state.\n'
            'Observed state: ${preparedWorkspace.stateName}\n'
            'Observed message: ${preparedWorkspace.inspectionMessage}\n'
            'Observed suggested workspace name: ${preparedWorkspace.suggestedWorkspaceName}\n'
            'Observed suggested write branch: ${preparedWorkspace.suggestedWriteBranch}\n'
            'Observed detected branch: ${preparedWorkspace.detectedWriteBranch}',
          );
        }

        await _pumpLocalWorkspaceOnboardingApp(
          tester,
          selectedPath: preparedWorkspace.repositoryPath,
        );

        final initialVisibleTexts = robot.visibleTexts();
        result['initial_visible_texts'] = initialVisibleTexts;

        await _openExistingFolder(tester);
        await _pumpUntil(
          tester,
          condition: () =>
              find
                  .text(_workspaceDetailsHeading, findRichText: true)
                  .evaluate()
                  .isNotEmpty &&
              robot
                  .labeledTextField(_workspaceNameLabel)
                  .evaluate()
                  .isNotEmpty &&
              robot.labeledTextField(_writeBranchLabel).evaluate().isNotEmpty &&
              find
                  .text(preparedWorkspace!.repositoryPath, findRichText: true)
                  .evaluate()
                  .isNotEmpty,
          timeout: const Duration(seconds: 10),
          failureMessage:
              'TS-720 could not reach the Workspace details step after selecting $_expectedFolderName. '
              'Visible texts: ${_formatSnapshot(robot.visibleTexts())}. '
              'Visible semantics: ${_formatSnapshot(robot.visibleSemanticsLabelsSnapshot())}.',
        );

        final failures = <String>[];
        final detailsVisibleTexts = robot.visibleTexts();
        final visibleSemantics = robot.visibleSemanticsLabelsSnapshot();
        final workspaceNameValue = robot.textFieldValue(_workspaceNameLabel);
        final writeBranchValue = robot.textFieldValue(_writeBranchLabel);
        final folderVisible = find
            .text(preparedWorkspace.repositoryPath, findRichText: true)
            .evaluate()
            .isNotEmpty;

        result['details_visible_texts'] = detailsVisibleTexts;
        result['details_visible_semantics'] = visibleSemantics;
        result['details_workspace_name_value'] = workspaceNameValue;
        result['details_write_branch_value'] = writeBranchValue;
        result['details_folder_visible'] = folderVisible;

        final step12Observed =
            'workspace_details_visible=${detailsVisibleTexts.contains(_workspaceDetailsHeading)}; '
            'selected_folder_visible=$folderVisible; '
            'status_visible=${detailsVisibleTexts.contains(_statusLabel)}; '
            'visible_texts=${detailsVisibleTexts.join(' | ')}';
        final step12Failures = <String>[];
        for (final text in const <String>[
          _workspaceDetailsHeading,
          _selectedFolderLabel,
          _workspaceNameLabel,
          _writeBranchLabel,
          _workspaceNameHelper,
          _writeBranchHelper,
          _statusLabel,
          _statusMessage,
          _changeFolderLabel,
          _submitLabel,
        ]) {
          if (!detailsVisibleTexts.contains(text)) {
            step12Failures.add(
              'The Workspace details step did not visibly render "$text".',
            );
          }
        }
        if (!folderVisible) {
          step12Failures.add(
            'The selected folder path ${preparedWorkspace.repositoryPath} was not visible in the Selected folder area.',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: step12Failures.isEmpty ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: step12Observed,
        );
        _recordStep(
          result,
          step: 2,
          status: step12Failures.isEmpty ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: step12Observed,
        );
        failures.addAll(
          step12Failures.map((message) => 'Steps 1-2 failed: $message'),
        );

        final step3Observed =
            'workspace_name="$workspaceNameValue"; write_branch="$writeBranchValue"; '
            'expected_workspace_name="$_expectedFolderName"; expected_write_branch="$_expectedBranch"';
        final step3Failures = <String>[];
        if (workspaceNameValue != _expectedFolderName) {
          step3Failures.add(
            'The Workspace name field proposed "$workspaceNameValue" instead of the folder-derived "$_expectedFolderName" display name.',
          );
        }
        if (writeBranchValue != _expectedBranch) {
          step3Failures.add(
            'The Write Branch field proposed "$writeBranchValue" instead of preserving the detected repository branch "$_expectedBranch".',
          );
        }
        _recordStep(
          result,
          step: 3,
          status: step3Failures.isEmpty ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: step3Observed,
        );
        failures.addAll(
          step3Failures.map((message) => 'Step 3 failed: $message'),
        );

        await _enterTextField(
          tester,
          robot.labeledTextField(_workspaceNameLabel),
          _editedWorkspaceName,
        );
        await _enterTextField(
          tester,
          robot.labeledTextField(_writeBranchLabel),
          _editedWriteBranch,
        );
        final editedWorkspaceNameValue = robot.textFieldValue(
          _workspaceNameLabel,
        );
        final editedWriteBranchValue = robot.textFieldValue(_writeBranchLabel);
        result['edited_workspace_name_value'] = editedWorkspaceNameValue;
        result['edited_write_branch_value'] = editedWriteBranchValue;

        final step4Observed =
            'edited_workspace_name="$editedWorkspaceNameValue"; edited_write_branch="$editedWriteBranchValue"';
        final step4Failures = <String>[];
        if (editedWorkspaceNameValue != _editedWorkspaceName) {
          step4Failures.add(
            'The Workspace name field did not keep the user-edited value "$_editedWorkspaceName".',
          );
        }
        if (editedWriteBranchValue != _editedWriteBranch) {
          step4Failures.add(
            'The Write Branch field did not keep the user-edited value "$_editedWriteBranch".',
          );
        }
        _recordStep(
          result,
          step: 4,
          status: step4Failures.isEmpty ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step4Observed,
        );
        failures.addAll(
          step4Failures.map((message) => 'Step 4 failed: $message'),
        );

        final focusCandidates = <String, Finder>{
          _changeFolderLabel: robot.actionButton(_changeFolderLabel),
          _workspaceNameLabel: robot.labeledTextField(_workspaceNameLabel),
          _writeBranchLabel: robot.labeledTextField(_writeBranchLabel),
          _submitLabel: robot.actionButton(_submitLabel),
        };
        await robot.clearFocus();
        final focusOrder = await robot.collectFocusOrder(
          candidates: focusCandidates,
          tabs: 20,
        );
        result['focus_order'] = focusOrder;

        final detailsHeadingContrast = _textContrastOnPage(
          robot,
          text: _workspaceDetailsHeading,
          minimumContrast: 4.5,
        );
        final workspaceNameContrast = _fieldLabelContrast(
          robot,
          label: _workspaceNameLabel,
          minimumContrast: 4.5,
        );
        final writeBranchContrast = _fieldLabelContrast(
          robot,
          label: _writeBranchLabel,
          minimumContrast: 4.5,
        );
        final submitButtonContrast = _buttonContrast(
          robot,
          label: _submitLabel,
          minimumContrast: 4.5,
        );
        final contrastObservations = <_ContrastObservation>[
          detailsHeadingContrast,
          workspaceNameContrast,
          writeBranchContrast,
          submitButtonContrast,
        ];
        result['contrast'] = contrastObservations
            .map((observation) => observation.toJson())
            .toList();

        final step5Observed =
            'focus_order=${focusOrder.join(' -> ')}; '
            'contrast=${contrastObservations.map((observation) => observation.describe()).join(' || ')}';
        final step5Failures = <String>[];

        final changeFolderIndex = focusOrder.indexOf(_changeFolderLabel);
        final workspaceNameIndex = focusOrder.indexOf(_workspaceNameLabel);
        final writeBranchIndex = focusOrder.indexOf(_writeBranchLabel);
        final submitIndex = focusOrder.indexOf(_submitLabel);

        if (changeFolderIndex == -1 ||
            workspaceNameIndex == -1 ||
            writeBranchIndex == -1 ||
            submitIndex == -1) {
          step5Failures.add(
            'Keyboard Tab traversal did not reach all expected Workspace details controls. '
            'Observed focus order: ${_formatSnapshot(focusOrder)}.',
          );
        } else if (!(changeFolderIndex < workspaceNameIndex &&
            workspaceNameIndex < writeBranchIndex &&
            writeBranchIndex < submitIndex)) {
          step5Failures.add(
            'Keyboard Tab traversal was not logical for the Workspace details flow. '
            'Observed focus order: ${_formatSnapshot(focusOrder)}.',
          );
        }

        final failingContrast = contrastObservations
            .where((observation) => !observation.passes)
            .toList(growable: false);
        if (failingContrast.isNotEmpty) {
          step5Failures.add(
            'AA contrast checks failed for ${failingContrast.map((observation) => observation.label).join(', ')}. '
            'Observed: ${failingContrast.map((observation) => observation.describe()).join(' || ')}.',
          );
        }

        _recordStep(
          result,
          step: 5,
          status: step5Failures.isEmpty ? 'passed' : 'failed',
          action: _requestSteps[4],
          observed: step5Observed,
        );
        failures.addAll(
          step5Failures.map((message) => 'Step 5 failed: $message'),
        );

        _recordHumanVerification(
          result,
          check:
              'Viewed the first-run local onboarding screen after picking the alpha-project folder, exactly as a user would encounter the Workspace details step.',
          observed:
              'status=${detailsVisibleTexts.contains(_statusLabel) ? _statusLabel : '<missing>'}; folder_path_visible=$folderVisible; visible_texts=${detailsVisibleTexts.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the user-facing details content rather than internal state: Selected folder, Workspace details, Workspace name helper copy, Write Branch helper copy, and the initialization status message.',
          observed:
              'folder=${preparedWorkspace.repositoryPath}; workspace_name="$workspaceNameValue"; write_branch="$writeBranchValue"; message_present=${detailsVisibleTexts.contains(_statusMessage)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Edited both visible fields to confirm they behaved like user-editable inputs before finishing the flow.',
          observed:
              'edited_workspace_name="$editedWorkspaceNameValue"; edited_write_branch="$editedWriteBranchValue"',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(result);
        fail('$error');
      } finally {
        preparedWorkspace?.dispose();
        semantics.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 90)),
  );
}

Future<void> _pumpLocalWorkspaceOnboardingApp(
  WidgetTester tester, {
  required String selectedPath,
}) async {
  SharedPreferences.setMockInitialValues(const <String, Object>{});
  tester.view.physicalSize = const Size(1440, 960);
  tester.view.devicePixelRatio = 1;

  await tester.pumpWidget(
    TrackStateApp(
      key: const ValueKey('ts-720-app'),
      repositoryFactory: () => const DemoTrackStateRepository(),
      workspaceProfileService: SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 12, 0),
      ),
      localWorkspaceOnboardingService: createLocalWorkspaceOnboardingService(),
      workspaceDirectoryPicker:
          ({String? confirmButtonText, String? initialDirectory}) async =>
              selectedPath,
      openLocalRepository:
          ({
            required String repositoryPath,
            required String defaultBranch,
            required String writeBranch,
          }) async => const DemoTrackStateRepository(),
    ),
  );
  await _pumpFrames(tester, frames: 12);
}

Future<void> _openExistingFolder(WidgetTester tester) async {
  final button = find.byKey(
    const ValueKey('local-workspace-onboarding-open-existing'),
  );
  await tester.ensureVisible(button);
  await tester.runAsync(() async {
    await tester.tap(button, warnIfMissed: false);
    await tester.pump();
    await Future<void>.delayed(const Duration(milliseconds: 500));
  });
  await _pumpFrames(tester, frames: 12);
}

Future<void> _enterTextField(
  WidgetTester tester,
  Finder field,
  String text,
) async {
  await tester.ensureVisible(field.first);
  await tester.tap(field.first, warnIfMissed: false);
  await tester.pump();
  await tester.enterText(field.first, text);
  await _pumpFrames(tester, frames: 8);
}

Future<_PreparedWorkspace> _prepareReadyWorkspace() async {
  final rootDirectory = await Directory.systemTemp.createTemp('ts-720-');
  final repositoryDirectory = Directory(
    '${rootDirectory.path}${Platform.pathSeparator}$_expectedFolderName',
  );
  await repositoryDirectory.create(recursive: true);

  await _runGit(repositoryDirectory.path, <String>[
    'init',
    '-b',
    _expectedBranch,
  ]);
  await _runGit(repositoryDirectory.path, <String>[
    'config',
    'user.email',
    'ts720@example.com',
  ]);
  await _runGit(repositoryDirectory.path, <String>[
    'config',
    'user.name',
    'TS-720 Test',
  ]);

  final readme = File(
    '${repositoryDirectory.path}${Platform.pathSeparator}README.md',
  );
  readme.writeAsStringSync('# $_expectedFolderName\n');
  await _runGit(repositoryDirectory.path, <String>['add', 'README.md']);
  await _runGit(repositoryDirectory.path, <String>[
    'commit',
    '-m',
    'Initial commit',
  ]);

  final inspection = await createLocalWorkspaceOnboardingService()
      .inspectFolder(repositoryDirectory.path);
  return _PreparedWorkspace(
    rootDirectory: rootDirectory,
    repositoryPath: repositoryDirectory.path,
    inspection: inspection,
  );
}

Future<void> _runGit(String workingDirectory, List<String> arguments) async {
  final result = await Process.run(
    'git',
    arguments,
    workingDirectory: workingDirectory,
  );
  if (result.exitCode == 0) {
    return;
  }
  throw ProcessException(
    'git',
    arguments,
    'exitCode=${result.exitCode}\nstdout=${result.stdout}\nstderr=${result.stderr}',
  );
}

Future<void> _pumpUntil(
  WidgetTester tester, {
  required bool Function() condition,
  required Duration timeout,
  required String failureMessage,
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (condition()) {
      return;
    }
    await tester.pump(const Duration(milliseconds: 100));
  }
  if (condition()) {
    return;
  }
  fail(failureMessage);
}

Future<void> _pumpFrames(WidgetTester tester, {required int frames}) async {
  for (var frame = 0; frame < frames; frame += 1) {
    await tester.pump(const Duration(milliseconds: 16));
  }
}

_ContrastObservation _textContrastOnPage(
  SettingsScreenRobot robot, {
  required String text,
  required double minimumContrast,
}) {
  final ratio = contrastRatio(
    robot.renderedTextColor(find.text(text, findRichText: true).first),
    robot.colors().surface,
  );
  return _ContrastObservation(
    label: text,
    text: text,
    contrastRatio: ratio,
    minimumContrast: minimumContrast,
  );
}

_ContrastObservation _fieldLabelContrast(
  SettingsScreenRobot robot, {
  required String label,
  required double minimumContrast,
}) {
  final field = robot.labeledTextField(label);
  final background =
      robot.decoratedContainerBackgroundColor(field) ?? robot.colors().surface;
  final ratio = contrastRatio(
    robot.renderedTextColorWithin(field, label),
    background,
  );
  return _ContrastObservation(
    label: label,
    text: label,
    contrastRatio: ratio,
    minimumContrast: minimumContrast,
  );
}

_ContrastObservation _buttonContrast(
  SettingsScreenRobot robot, {
  required String label,
  required double minimumContrast,
}) {
  final button = robot.actionButton(label);
  final ratio = contrastRatio(
    robot.resolvedButtonForeground(button, <WidgetState>{}, text: label),
    robot.renderedButtonBackground(button),
  );
  return _ContrastObservation(
    label: label,
    text: label,
    contrastRatio: ratio,
    minimumContrast: minimumContrast,
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
  final error = '${result['error'] ?? 'Unknown error'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
}

String _jiraComment(Map<String, Object?> result, {required bool passed}) {
  final steps = _steps(result);
  final checks = _humanChecks(result);
  final status = passed ? 'PASSED' : 'FAILED';
  final buffer = StringBuffer()
    ..writeln('h3. Test Automation Result — $status')
    ..writeln()
    ..writeln('*Ticket:* $_ticketKey')
    ..writeln('*Summary:* $_ticketSummary')
    ..writeln('*Test file:* {{$_testFilePath}}')
    ..writeln('*Run command:* {{$_runCommand}}')
    ..writeln('*Environment:* flutter test widget harness on ${result['os']}')
    ..writeln(
      '*Workspace path:* {{${result['workspace_path'] ?? '<unknown>'}}}',
    )
    ..writeln()
    ..writeln('h4. Automated verification');
  for (final step in steps) {
    final icon = step['status'] == 'passed' ? '(/)' : '(x)';
    buffer
      ..writeln('$icon Step ${step['step']}: ${step['action']}')
      ..writeln('{noformat}${step['observed']}{noformat}');
  }
  buffer
    ..writeln()
    ..writeln('h4. Human-style verification');
  for (final check in checks) {
    buffer
      ..writeln('* ${check['check']}')
      ..writeln('{noformat}${check['observed']}{noformat}');
  }
  if (!passed) {
    buffer
      ..writeln()
      ..writeln('h4. Failure details')
      ..writeln(
        '{noformat}${result['error']}\n\n${result['traceback']}{noformat}',
      );
  }
  return buffer.toString();
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final steps = _steps(result);
  final checks = _humanChecks(result);
  final buffer = StringBuffer()
    ..writeln('## Test Automation Result: ${passed ? 'PASSED' : 'FAILED'}')
    ..writeln()
    ..writeln('| Field | Value |')
    ..writeln('| --- | --- |')
    ..writeln('| Ticket | $_ticketKey |')
    ..writeln('| Summary | $_ticketSummary |')
    ..writeln('| Test file | `$_testFilePath` |')
    ..writeln('| Run command | `$_runCommand` |')
    ..writeln(
      '| Environment | flutter test widget harness on ${result['os']} |',
    )
    ..writeln(
      '| Workspace path | `${result['workspace_path'] ?? '<unknown>'}` |',
    )
    ..writeln()
    ..writeln('### Automated verification');
  for (final step in steps) {
    final icon = step['status'] == 'passed' ? '✅' : '❌';
    buffer
      ..writeln('- $icon **Step ${step['step']}** — ${step['action']}')
      ..writeln('  - Observed: `${step['observed']}`');
  }
  buffer
    ..writeln()
    ..writeln('### Human-style verification');
  for (final check in checks) {
    buffer
      ..writeln('- **${check['check']}**')
      ..writeln('  - Observed: `${check['observed']}`');
  }
  if (!passed) {
    buffer
      ..writeln()
      ..writeln('### Failure details')
      ..writeln('```')
      ..writeln(result['error'])
      ..writeln()
      ..writeln(result['traceback'])
      ..writeln('```');
  }
  return buffer.toString();
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'passed' : 'failed';
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey $status')
    ..writeln()
    ..writeln('- Ticket: $_ticketSummary')
    ..writeln('- Test: `$_testFilePath`')
    ..writeln('- Run command: `$_runCommand`')
    ..writeln('- Workspace path: `${result['workspace_path'] ?? '<unknown>'}`')
    ..writeln(
      '- Result: ${passed ? '1 passed, 0 failed' : '0 passed, 1 failed'}',
    )
    ..writeln()
    ..writeln('## Automated verification');
  for (final step in _steps(result)) {
    buffer.writeln(
      '- Step ${step['step']} (${step['status']}): ${step['action']} — ${step['observed']}',
    );
  }
  buffer
    ..writeln()
    ..writeln('## Human-style verification');
  for (final check in _humanChecks(result)) {
    buffer.writeln('- ${check['check']} — ${check['observed']}');
  }
  if (!passed) {
    buffer
      ..writeln()
      ..writeln('## Failure')
      ..writeln()
      ..writeln('```')
      ..writeln(result['error'])
      ..writeln()
      ..writeln(result['traceback'])
      ..writeln('```');
  }
  return buffer.toString();
}

String _bugDescription(Map<String, Object?> result) {
  final steps = _steps(result);
  final workspacePath = '${result['workspace_path'] ?? '<unknown>'}';
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey automated failure')
    ..writeln()
    ..writeln('## Summary')
    ..writeln(_ticketSummary)
    ..writeln()
    ..writeln('## Steps to reproduce')
    ..writeln('1. ${_requestSteps[0]} ${_stepStatusSummary(steps, 1)}')
    ..writeln('2. ${_requestSteps[1]} ${_stepStatusSummary(steps, 2)}')
    ..writeln('3. ${_requestSteps[2]} ${_stepStatusSummary(steps, 3)}')
    ..writeln('4. ${_requestSteps[3]} ${_stepStatusSummary(steps, 4)}')
    ..writeln('5. ${_requestSteps[4]} ${_stepStatusSummary(steps, 5)}')
    ..writeln()
    ..writeln('## Actual vs Expected')
    ..writeln(
      '- **Expected:** the Workspace details step should propose `$_expectedFolderName` from the folder name, preserve `$_expectedBranch` as the detected write branch, keep both visible inputs editable, and expose a logical keyboard path with AA-compliant contrast.',
    )
    ..writeln('- **Actual:** ${_actualSummary(result)}')
    ..writeln()
    ..writeln('## Exact error')
    ..writeln('```')
    ..writeln(result['error'])
    ..writeln()
    ..writeln(result['traceback'])
    ..writeln('```')
    ..writeln()
    ..writeln('## Environment')
    ..writeln('- URL: N/A (local Flutter widget test harness)')
    ..writeln('- Browser: Flutter WidgetTester')
    ..writeln('- OS: ${result['os']}')
    ..writeln('- Workspace path: `$workspacePath`')
    ..writeln('- Run command: `$_runCommand`')
    ..writeln()
    ..writeln('## Relevant logs')
    ..writeln('```')
    ..writeln('initial_visible_texts: ${result['initial_visible_texts']}')
    ..writeln('details_visible_texts: ${result['details_visible_texts']}')
    ..writeln(
      'details_visible_semantics: ${result['details_visible_semantics']}',
    )
    ..writeln('focus_order: ${result['focus_order']}')
    ..writeln('contrast: ${result['contrast']}')
    ..writeln('```');
  return buffer.toString();
}

String _stepStatusSummary(List<Map<String, Object?>> steps, int stepNumber) {
  final step = steps.cast<Map<String, Object?>>().firstWhere(
    (candidate) => candidate['step'] == stepNumber,
    orElse: () => <String, Object?>{
      'status': 'not_run',
      'observed': 'Step did not execute.',
    },
  );
  final status = step['status'] == 'passed' ? '✅' : '❌';
  return '$status ${step['observed']}';
}

String _actualSummary(Map<String, Object?> result) {
  final failingSteps = _steps(result)
      .where((step) => step['status'] != 'passed')
      .map((step) => 'Step ${step['step']} observed ${step['observed']}')
      .toList(growable: false);
  if (failingSteps.isEmpty) {
    return 'The test threw an error before recording a failing step.';
  }
  return failingSteps.join(' ');
}

List<Map<String, Object?>> _steps(Map<String, Object?> result) {
  return (result['steps'] as List<Object?>? ?? const <Object?>[])
      .cast<Map<String, Object?>>();
}

List<Map<String, Object?>> _humanChecks(Map<String, Object?> result) {
  return (result['human_verification'] as List<Object?>? ?? const <Object?>[])
      .cast<Map<String, Object?>>();
}

String _formatSnapshot(List<String> values) {
  if (values.isEmpty) {
    return '<none>';
  }
  return values.join(' | ');
}

class _PreparedWorkspace {
  _PreparedWorkspace({
    required this.rootDirectory,
    required this.repositoryPath,
    required LocalWorkspaceInspection inspection,
  }) : _inspection = inspection;

  final Directory rootDirectory;
  final String repositoryPath;
  final LocalWorkspaceInspection _inspection;

  bool get canContinueOnboarding => _inspection.canInitialize;
  String get stateName => _inspection.state.name;
  String get inspectionMessage => _inspection.message;
  String get suggestedWorkspaceName => _inspection.suggestedWorkspaceName;
  String get suggestedWriteBranch => _inspection.suggestedWriteBranch;
  String? get detectedWriteBranch => _inspection.detectedWriteBranch;

  void dispose() {
    if (!rootDirectory.existsSync()) {
      return;
    }
    rootDirectory.deleteSync(recursive: true);
  }
}

class _ContrastObservation {
  const _ContrastObservation({
    required this.label,
    required this.text,
    required this.contrastRatio,
    required this.minimumContrast,
  });

  final String label;
  final String text;
  final double contrastRatio;
  final double minimumContrast;

  bool get passes => contrastRatio >= minimumContrast;

  Map<String, Object> toJson() => <String, Object>{
    'label': label,
    'text': text,
    'contrast_ratio': contrastRatio.toStringAsFixed(2),
    'minimum_contrast': minimumContrast.toStringAsFixed(1),
    'passes': passes,
  };

  String describe() =>
      '$label "$text" ${contrastRatio.toStringAsFixed(2)}:1 '
      '(minimum ${minimumContrast.toStringAsFixed(1)}:1)';
}
