import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../fixtures/workspace_onboarding_screen_fixture.dart';

const String _ticketKey = 'TS-701';
const String _ticketSummary =
    'First-launch onboarding exposes Local and Hosted as equal primary choices';
const String _testFilePath = 'testing/tests/TS-701/test_ts_701.dart';
const String _runCommand =
    'flutter test testing/tests/TS-701/test_ts_701.dart --reporter expanded';
const String _expectedFirstRunDescription =
    'Choose a local folder or hosted repository to get started.';

const List<String> _requestSteps = <String>[
  'Launch the TrackState application.',
  'Observe the initial screen content.',
  'Verify the visibility of the segmented choice control.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-701 first launch shows Local folder and Hosted repository as equal first-class choices',
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

      final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 20, 20),
      );

      try {
        final screen = await launchWorkspaceOnboardingFixture(
          tester,
          workspaceProfileService: workspaceProfileService,
          sharedPreferences: const <String, Object>{},
        );

        try {
          final initialState = screen.captureState();
          final choiceObservation = screen.observeTargetChoices();
          result['initial_visible_texts'] = initialState.visibleTexts;
          result['initial_interactive_semantics_labels'] =
              initialState.interactiveSemanticsLabels;
          result['choice_observation'] = choiceObservation.toJson();
          _recordHumanVerification(
            result,
            check:
                'Viewed the very first screen exactly as a new user would see it with no saved or migrated workspaces.',
            observed:
                'visible_texts=${_formatList(initialState.visibleTexts)}; interactive_semantics_labels=${_formatList(initialState.interactiveSemanticsLabels)}',
          );
          _recordHumanVerification(
            result,
            check:
                'Verified the choice controls from a user perspective by checking the visible Local folder and Hosted repository labels and their side-by-side layout.',
            observed: jsonEncode(choiceObservation.toJson()),
          );

          final failures = <String>[];

          final step1Passed =
              initialState.isOnboardingVisible &&
              !initialState.isDashboardVisible &&
              initialState.visibleTexts.contains('Add workspace');
          _recordStep(
            result,
            step: 1,
            status: step1Passed ? 'passed' : 'failed',
            action: _requestSteps[0],
            observed:
                'onboarding_visible=${initialState.isOnboardingVisible}; dashboard_visible=${initialState.isDashboardVisible}; visible_texts=${_formatList(initialState.visibleTexts)}',
          );
          if (!step1Passed) {
            failures.add(
              'Step 1 failed: launching the application in a fresh state did not open the onboarding route.\n'
              'Observed onboarding visible: ${initialState.isOnboardingVisible}\n'
              'Observed dashboard visible: ${initialState.isDashboardVisible}\n'
              'Observed visible texts: ${_formatList(initialState.visibleTexts)}',
            );
          }

          final missingExpectedTexts = <String>[
            if (!initialState.visibleTexts.contains(
              _expectedFirstRunDescription,
            ))
              _expectedFirstRunDescription,
            if (!initialState.visibleTexts.contains('Local folder'))
              'Local folder',
            if (!initialState.visibleTexts.contains('Hosted repository'))
              'Hosted repository',
          ];
          _recordStep(
            result,
            step: 2,
            status: missingExpectedTexts.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[1],
            observed:
                'missing_texts=${_formatList(missingExpectedTexts)}; visible_texts=${_formatList(initialState.visibleTexts)}',
          );
          if (missingExpectedTexts.isNotEmpty) {
            failures.add(
              'Step 2 failed: the first-launch onboarding content did not match the ticket expectation.\n'
              'Missing visible texts: ${_formatList(missingExpectedTexts)}\n'
              'Observed visible texts: ${_formatList(initialState.visibleTexts)}\n'
              'Observed interactive semantics labels: ${_formatList(initialState.interactiveSemanticsLabels)}',
            );
          }

          _recordStep(
            result,
            step: 3,
            status: choiceObservation.hasEqualFirstClassChoices
                ? 'passed'
                : 'failed',
            action: _requestSteps[2],
            observed: jsonEncode(choiceObservation.toJson()),
          );
          if (!choiceObservation.hasEqualFirstClassChoices) {
            failures.add(
              'Step 3 failed: the first-launch onboarding screen did not expose Local folder and Hosted repository as equal first-class choices.\n'
              'Observed choice layout: ${jsonEncode(choiceObservation.toJson())}\n'
              'Observed visible texts: ${_formatList(initialState.visibleTexts)}\n'
              'Observed interactive semantics labels: ${_formatList(initialState.interactiveSemanticsLabels)}',
            );
          }

          if (failures.isNotEmpty) {
            throw AssertionError(failures.join('\n\n'));
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
    timeout: const Timeout(Duration(seconds: 60)),
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
    '* Launched the production first-launch flow with an empty SharedPreferences-backed workspace profile store.',
    '* Checked the first visible screen content for the onboarding route heading, first-run description, and the ticket-required {noformat}Local folder{noformat} and {noformat}Hosted repository{noformat} choices.',
    '* Verified the user-facing choice controls behave like equal first-class options by checking their visibility, semantics labels, and side-by-side layout observation.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the first-launch onboarding route showed the dedicated card UI with both {noformat}Local folder{noformat} and {noformat}Hosted repository{noformat} as equal primary choices.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Initial visible texts: {noformat}${_formatList(_resultList(result['initial_visible_texts']))}{noformat}',
    '* Initial semantics labels: {noformat}${_formatList(_resultList(result['initial_interactive_semantics_labels']))}{noformat}',
    '* Choice observation: {noformat}${jsonEncode(result['choice_observation'])}{noformat}',
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
    '- Launched the production first-launch flow with an empty SharedPreferences-backed workspace profile store.',
    '- Checked the first visible screen content for the onboarding route heading, first-run description, and the ticket-required `Local folder` and `Hosted repository` choices.',
    '- Verified the user-facing choice controls behave like equal first-class options by checking their visibility, semantics labels, and side-by-side layout observation.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the first-launch onboarding route showed the dedicated card UI with both `Local folder` and `Hosted repository` as equal primary choices.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Initial visible texts: `${_formatList(_resultList(result['initial_visible_texts']))}`',
    '- Initial semantics labels: `${_formatList(_resultList(result['initial_interactive_semantics_labels']))}`',
    '- Choice observation: `${jsonEncode(result['choice_observation'])}`',
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
    '# $_ticketKey - $_ticketSummary',
    '',
    '- Status: $statusLabel',
    '- Run command: `$_runCommand`',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Initial visible texts: `${_formatList(_resultList(result['initial_visible_texts']))}`',
    '- Initial semantics labels: `${_formatList(_resultList(result['initial_interactive_semantics_labels']))}`',
    '- Choice observation: `${jsonEncode(result['choice_observation'])}`',
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
    '## Summary',
    'Fresh first launch does not show the dedicated onboarding route with `Local folder` and `Hosted repository` as equal first-class choices.',
    '',
    '## Environment',
    '- URL/App: `flutter test` widget runtime for `TrackStateApp`',
    '- OS: `${Platform.operatingSystem}`',
    '- Workspace state: empty SharedPreferences-backed workspace profile store with no saved or migrated workspaces',
    '- Test file: `$_testFilePath`',
    '- Run command: `$_runCommand`',
    '',
    '## Exact steps to reproduce',
    '1. Launch the TrackState application with a fresh state and no saved or migrated workspaces in SharedPreferences. ${_bugStepStatus(result, 1)}',
    '   - Actual: ${_bugStepObserved(result, 1)}',
    '2. Observe the initial screen content. ${_bugStepStatus(result, 2)}',
    '   - Actual: ${_bugStepObserved(result, 2)}',
    '3. Verify the visibility of the segmented choice control. ${_bugStepStatus(result, 3)}',
    '   - Actual: ${_bugStepObserved(result, 3)}',
    '',
    '## Expected result',
    'The application should open the onboarding route and show a card-based UI with a segmented choice control containing `Local folder` and `Hosted repository` as equal primary options.',
    '',
    '## Actual result',
    'The initial first-launch screen stays on the legacy local-only onboarding content instead of rendering the ticket-required dual-choice onboarding route.',
    '- Initial visible texts: `${_formatList(_resultList(result['initial_visible_texts']))}`',
    '- Initial semantics labels: `${_formatList(_resultList(result['initial_interactive_semantics_labels']))}`',
    '- Choice observation: `${jsonEncode(result['choice_observation'])}`',
    '',
    '## Exact error message or assertion failure',
    '```',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Relevant logs',
    '```',
    'initial_visible_texts=${_formatList(_resultList(result['initial_visible_texts']))}',
    'initial_interactive_semantics_labels=${_formatList(_resultList(result['initial_interactive_semantics_labels']))}',
    'choice_observation=${jsonEncode(result['choice_observation'])}',
    '```',
  ];
  return '${lines.join('\n')}\n';
}

Iterable<String> _jiraStepLines(Map<String, Object?> result) sync* {
  for (final step in _resultSteps(result)) {
    yield '* Step ${step['step']} (${step['status']}): ${step['action']}';
    yield '** Observed: {noformat}${step['observed']}{noformat}';
  }
}

Iterable<String> _markdownStepLines(Map<String, Object?> result) sync* {
  for (final step in _resultSteps(result)) {
    yield '- Step ${step['step']} (${step['status']}): ${step['action']}';
    yield '  - Observed: `${step['observed']}`';
  }
}

Iterable<String> _jiraHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final check in _resultChecks(result)) {
    yield '* ${check['check']}';
    yield '** Observed: {noformat}${check['observed']}{noformat}';
  }
}

Iterable<String> _markdownHumanVerificationLines(
  Map<String, Object?> result,
) sync* {
  for (final check in _resultChecks(result)) {
    yield '- ${check['check']}';
    yield '  - Observed: `${check['observed']}`';
  }
}

List<Map<String, Object?>> _resultSteps(Map<String, Object?> result) {
  return (result['steps'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
}

List<Map<String, Object?>> _resultChecks(Map<String, Object?> result) {
  return (result['human_verification'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
}

String _bugStepStatus(Map<String, Object?> result, int stepNumber) {
  final step = _stepByNumber(result, stepNumber);
  final status = '${step?['status'] ?? 'failed'}';
  return status == 'passed' ? 'Passed ✅' : 'Failed ❌';
}

String _bugStepObserved(Map<String, Object?> result, int stepNumber) {
  final step = _stepByNumber(result, stepNumber);
  return '${step?['observed'] ?? '<missing>'}';
}

Map<String, Object?>? _stepByNumber(
  Map<String, Object?> result,
  int stepNumber,
) {
  for (final step in _resultSteps(result)) {
    if (step['step'] == stepNumber) {
      return step;
    }
  }
  return null;
}

List<Object?> _resultList(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  return const <Object?>[];
}

String _formatList(List<Object?> values) {
  if (values.isEmpty) {
    return '<empty>';
  }
  return values.map((value) => value.toString()).join(' | ');
}
