import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';

import '../../fixtures/workspace_onboarding_screen_fixture.dart';

const String _ticketKey = 'TS-1151';
const String _ticketSummary =
    'First-launch onboarding with no profiles shows Hosted repository fields';
const String _testFilePath = 'testing/tests/TS-1151/test_ts_1151.dart';
const String _runCommand =
    'flutter test testing/tests/TS-1151/test_ts_1151.dart --reporter expanded';
const String _expectedResult =
    "The application explicitly enables the hosted setup path on first launch; the visible 'Repository' and 'Branch' inputs, the repository helper copy, and the keyboard focus path are rendered according to the hosted onboarding UI contract.";

const List<String> _requestSteps = <String>[
  'Launch the TrackState application.',
  "Confirm the onboarding screen displays the selection toggle for 'Local folder' and 'Hosted repository'.",
  "Select the 'Hosted repository' option if it is not selected by default.",
  "Verify that the hosted 'Repository' and 'Branch' input fields and helper copy are rendered and visible.",
  'Use the keyboard (Tab key) to navigate through the rendered controls.',
];

const List<String> _initialChoiceTexts = <String>[
  'Add workspace',
  'Local folder',
  'Hosted repository',
];

const List<String> _hostedFieldTexts = <String>['Repository', 'Branch'];
const List<String> _hostedHelperTexts = <String>[
  'Enter the repository as owner/repo.',
  'Connect GitHub in an existing hosted workspace to browse accessible repositories. You can still enter owner/repo manually here.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-1151 first launch exposes the hosted onboarding fields and keyboard path',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'expected_result': _expectedResult,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 26, 23, 31, 32),
      );

      try {
        final screen = await launchWorkspaceOnboardingFixture(
          tester,
          workspaceProfileService: workspaceProfileService,
          sharedPreferences: const <String, Object>{},
        );

        try {
          final failures = <String>[];

          final initialState = screen.captureState();
          result['initial_visible_texts'] = initialState.visibleTexts;
          result['initial_interactive_semantics_labels'] =
              initialState.interactiveSemanticsLabels;

          final step1Passed =
              initialState.isOnboardingVisible &&
              !initialState.isDashboardVisible &&
              _missingExpectedTexts(
                expected: _initialChoiceTexts,
                observed: initialState.visibleTexts,
              ).isEmpty;
          _recordStep(
            result,
            step: 1,
            status: step1Passed ? 'passed' : 'failed',
            action: _requestSteps[0],
            observed:
                'onboarding_visible=${initialState.isOnboardingVisible}; '
                'dashboard_visible=${initialState.isDashboardVisible}; '
                'visible_texts=${_formatList(initialState.visibleTexts)}',
          );
          if (!step1Passed) {
            failures.add(
              'Step 1 failed: launching the application in a fresh state did not open the expected first-launch onboarding route.\n'
              'Observed onboarding visible: ${initialState.isOnboardingVisible}\n'
              'Observed dashboard visible: ${initialState.isDashboardVisible}\n'
              'Observed visible texts: ${_formatList(initialState.visibleTexts)}',
            );
          }

          final missingChoiceTexts = _missingExpectedTexts(
            expected: const <String>['Local folder', 'Hosted repository'],
            observed: initialState.visibleTexts,
          );
          _recordStep(
            result,
            step: 2,
            status: missingChoiceTexts.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[1],
            observed:
                'missing_choice_texts=${_formatList(missingChoiceTexts)}; '
                'visible_texts=${_formatList(initialState.visibleTexts)}; '
                'interactive_labels=${_formatList(initialState.interactiveSemanticsLabels)}',
          );
          if (missingChoiceTexts.isNotEmpty) {
            failures.add(
              'Step 2 failed: the first-launch onboarding screen did not expose the required Local folder and Hosted repository choices.\n'
              'Missing choice labels: ${_formatList(missingChoiceTexts)}\n'
              'Observed visible texts: ${_formatList(initialState.visibleTexts)}\n'
              'Observed interactive semantics labels: ${_formatList(initialState.interactiveSemanticsLabels)}',
            );
          }

          await screen.chooseHostedRepository();
          final hostedState = screen.captureState();
          result['hosted_visible_texts'] = hostedState.visibleTexts;
          result['hosted_interactive_semantics_labels'] =
              hostedState.interactiveSemanticsLabels;
          result['hosted_repository_value'] = hostedState.hostedRepositoryValue;
          result['hosted_branch_value'] = hostedState.hostedBranchValue;

          final step3Passed =
              hostedState.isOnboardingVisible &&
              hostedState.hostedRepositoryValue != null &&
              hostedState.hostedBranchValue != null;
          _recordStep(
            result,
            step: 3,
            status: step3Passed ? 'passed' : 'failed',
            action: _requestSteps[2],
            observed:
                'onboarding_visible=${hostedState.isOnboardingVisible}; '
                'hosted_repository_field_visible=${hostedState.hostedRepositoryValue != null}; '
                'hosted_branch_field_visible=${hostedState.hostedBranchValue != null}; '
                'visible_texts=${_formatList(hostedState.visibleTexts)}',
          );
          if (!step3Passed) {
            failures.add(
              'Step 3 failed: selecting Hosted repository did not render the hosted onboarding form.\n'
              'Observed onboarding visible: ${hostedState.isOnboardingVisible}\n'
              'Observed hosted repository field visible: ${hostedState.hostedRepositoryValue != null}\n'
              'Observed hosted branch field visible: ${hostedState.hostedBranchValue != null}\n'
              'Observed visible texts: ${_formatList(hostedState.visibleTexts)}',
            );
          }

          final missingHostedTexts = _missingExpectedTexts(
            expected: <String>[..._hostedFieldTexts, ..._hostedHelperTexts],
            observed: hostedState.visibleTexts,
          );
          final hostedFieldValuesVisible =
              hostedState.hostedRepositoryValue != null &&
              hostedState.hostedBranchValue != null;
          final fieldSemantics = <String>[
            if (hostedState.hostedRepositoryValue != null) 'repository-field',
            if (hostedState.hostedBranchValue != null) 'branch-field',
          ];
          _recordStep(
            result,
            step: 4,
            status: missingHostedTexts.isEmpty && hostedFieldValuesVisible
                ? 'passed'
                : 'failed',
            action: _requestSteps[3],
            observed:
                'missing_hosted_texts=${_formatList(missingHostedTexts)}; '
                'visible_texts=${_formatList(hostedState.visibleTexts)}; '
                'interactive_labels=${_formatList(hostedState.interactiveSemanticsLabels)}; '
                'repository_value=${hostedState.hostedRepositoryValue}; '
                'branch_value=${hostedState.hostedBranchValue}; '
                'rendered_fields=${_formatList(fieldSemantics)}',
          );
          if (missingHostedTexts.isNotEmpty || !hostedFieldValuesVisible) {
            failures.add(
              'Step 4 failed: the hosted onboarding form did not visibly render the hosted UI contract.\n'
              'Expected visible texts: ${_formatList(<String>[..._hostedFieldTexts, ..._hostedHelperTexts])}\n'
              'Missing visible texts: ${_formatList(missingHostedTexts)}\n'
              'Observed visible texts: ${_formatList(hostedState.visibleTexts)}\n'
              'Observed interactive semantics labels: ${_formatList(hostedState.interactiveSemanticsLabels)}\n'
              'Hosted repository field visible: ${hostedState.hostedRepositoryValue != null}\n'
              'Hosted branch field visible: ${hostedState.hostedBranchValue != null}',
            );
          }

          List<String> focusOrder = const <String>[];
          if (hostedState.hostedRepositoryValue == null ||
              hostedState.hostedBranchValue == null) {
            _recordStep(
              result,
              step: 5,
              status: 'failed',
              action: _requestSteps[4],
              observed:
                  'keyboard_path_unavailable=true; '
                  'hosted_repository_field_visible=${hostedFieldValuesVisible && hostedState.hostedRepositoryValue != null}; '
                  'hosted_branch_field_visible=${hostedFieldValuesVisible && hostedState.hostedBranchValue != null}',
            );
            failures.add(
              'Step 5 failed: the keyboard path could not be exercised because the hosted repository form fields were not rendered.',
            );
          } else {
            focusOrder = await screen.collectHostedRepositoryFocusOrder();
            result['focus_order'] = focusOrder;

            final localIndex = focusOrder.indexOf('Local folder');
            final hostedIndex = focusOrder.indexOf('Hosted repository');
            final repositoryIndex = focusOrder.indexOf('Repository field');
            final branchIndex = focusOrder.indexOf('Branch field');
            final openIndex = focusOrder.indexOf('Open');
            final focusFailures = <String>[];

            if (localIndex == -1 ||
                hostedIndex == -1 ||
                repositoryIndex == -1 ||
                branchIndex == -1) {
              focusFailures.add(
                'Keyboard Tab traversal did not reach all expected hosted onboarding controls. '
                'Observed focus order: ${_formatList(focusOrder)}.',
              );
            } else if (!(localIndex < hostedIndex &&
                hostedIndex < repositoryIndex &&
                repositoryIndex < branchIndex)) {
              focusFailures.add(
                'Keyboard Tab traversal was not logical for the first-launch hosted onboarding flow. '
                'Observed focus order: ${_formatList(focusOrder)}.',
              );
            }

            if (openIndex != -1 && !(branchIndex < openIndex)) {
              focusFailures.add(
                'Keyboard Tab traversal reached the Open action before leaving the hosted Branch field. '
                'Observed focus order: ${_formatList(focusOrder)}.',
              );
            }

            _recordStep(
              result,
              step: 5,
              status: focusFailures.isEmpty ? 'passed' : 'failed',
              action: _requestSteps[4],
              observed: 'focus_order=${_formatList(focusOrder)}',
            );
            failures.addAll(
              focusFailures.map((message) => 'Step 5 failed: $message'),
            );
          }

          _recordHumanVerification(
            result,
            check:
                'Viewed the fresh first-launch onboarding route exactly as a new user would see it before any workspace profile existed.',
            observed:
                'visible_texts=${_formatList(initialState.visibleTexts)}; '
                'interactive_labels=${_formatList(initialState.interactiveSemanticsLabels)}',
          );
          _recordHumanVerification(
            result,
            check:
                'Switched to the Hosted repository path and verified the visible hosted labels, helper copy, field values, and keyboard traversal from the user-facing controls.',
            observed:
                'visible_texts=${_formatList(hostedState.visibleTexts)}; '
                'interactive_labels=${_formatList(hostedState.interactiveSemanticsLabels)}; '
                'repository_value=${hostedState.hostedRepositoryValue}; '
                'branch_value=${hostedState.hostedBranchValue}; '
                'focus_order=${_formatList(focusOrder)}',
          );

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
        _writeFailureOutputs(
          result,
          writeBugDescription: error is AssertionError,
        );
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        semantics.dispose();
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

void _writeFailureOutputs(
  Map<String, Object?> result, {
  required bool writeBugDescription,
}) {
  _outputsDir.createSync(recursive: true);
  final error = '${result['error'] ?? 'AssertionError: unknown failure'}';
  _resultFile.writeAsStringSync(
    '${jsonEncode(<String, Object>{'status': 'failed', 'passed': 0, 'failed': 1, 'skipped': 0, 'summary': '0 passed, 1 failed', 'error': error})}\n',
  );
  _jiraCommentFile.writeAsStringSync(_jiraComment(result, passed: false));
  _prBodyFile.writeAsStringSync(_prBody(result, passed: false));
  _responseFile.writeAsStringSync(_responseSummary(result, passed: false));
  if (writeBugDescription) {
    _bugDescriptionFile.writeAsStringSync(_bugDescription(result));
  } else if (_bugDescriptionFile.existsSync()) {
    _bugDescriptionFile.deleteSync();
  }
}

String _jiraComment(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    'h3. Test Automation Result',
    '',
    '*Status:* $statusLabel',
    '*Test Case:* $_ticketKey - $_ticketSummary',
    '',
    'h4. What was checked by automation',
    '* Launched the production first-launch onboarding route with an empty SharedPreferences-backed workspace profile store.',
    '* Verified the visible first-launch choices for {noformat}Local folder{noformat} and {noformat}Hosted repository{noformat}.',
    '* Switched to the hosted onboarding path and checked the visible {noformat}Repository{noformat} and {noformat}Branch{noformat} labels, hosted helper copy, and rendered hosted field values.',
    '* Used keyboard Tab navigation to capture the hosted onboarding focus path across the rendered controls.',
    '',
    'h4. Human-style verification',
    ..._jiraHumanVerificationLines(result),
    '',
    'h4. Observed result',
    passed
        ? '* Matched the expected result: the fresh first-launch flow exposed the hosted setup path, showed the hosted Repository/Branch contract and helper copy, and keyboard traversal reached the hosted inputs in logical order.'
        : '* Did not match the expected result. See the failed step details, visible texts, focus order, and exact assertion below.',
    '* Expected result: {noformat}${result['expected_result']}{noformat}',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Initial visible texts: {noformat}${_formatList(_resultList(result['initial_visible_texts']))}{noformat}',
    '* Hosted visible texts: {noformat}${_formatList(_resultList(result['hosted_visible_texts']))}{noformat}',
    '* Hosted semantics labels: {noformat}${_formatList(_resultList(result['hosted_interactive_semantics_labels']))}{noformat}',
    '* Focus order: {noformat}${_formatList(_resultList(result['focus_order']))}{noformat}',
    '',
    'h4. Step results',
    ..._jiraStepLines(result),
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
      '{code}',
      '${result['error'] ?? 'Unknown error'}',
      '',
      '${result['traceback'] ?? ''}',
      '{code}',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? '✅ PASSED' : '❌ FAILED';
  final lines = <String>[
    '# Test Automation Result',
    '',
    '- **Status:** $statusLabel',
    '- **Test Case:** $_ticketKey - $_ticketSummary',
    '- **Environment:** `flutter test / ${Platform.operatingSystem}`',
    '- **Run command:** `$_runCommand`',
    '',
    '## What was checked by automation',
    '- Launched the production first-launch onboarding route with no saved workspace profiles.',
    '- Verified the visible `Local folder` and `Hosted repository` chooser controls.',
    '- Switched to the hosted path and checked the visible `Repository` and `Branch` labels, hosted helper copy, and rendered hosted field values.',
    '- Captured the keyboard Tab path across the rendered hosted onboarding controls.',
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '## Observed result',
    passed
        ? '- Matched the expected result: the hosted first-launch path was visible, the hosted Repository/Branch contract was rendered, and keyboard traversal reached those inputs in logical order.'
        : '- Did not match the expected result. See the failed step details, actual visible texts, and exact error.',
    '- **Expected result:**',
    '',
    '```text',
    '${result['expected_result']}',
    '```',
    '',
    '- **Initial visible texts:**',
    '',
    '```text',
    _formatList(_resultList(result['initial_visible_texts'])),
    '```',
    '',
    '- **Hosted visible texts:**',
    '',
    '```text',
    _formatList(_resultList(result['hosted_visible_texts'])),
    '```',
    '',
    '- **Hosted semantics labels:**',
    '',
    '```text',
    _formatList(_resultList(result['hosted_interactive_semantics_labels'])),
    '```',
    '',
    '- **Focus order:**',
    '',
    '```text',
    _formatList(_resultList(result['focus_order'])),
    '```',
    '',
    '## Step results',
    ..._markdownStepLines(result),
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '',
      '```text',
      '${result['error'] ?? 'Unknown error'}',
      '',
      '${result['traceback'] ?? ''}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final statusLabel = passed ? 'PASSED' : 'FAILED';
  final lines = <String>[
    '# $_ticketKey $statusLabel',
    '',
    '- **Test case:** $_ticketSummary',
    '- **Run command:** `$_runCommand`',
    '- **Environment:** `flutter test / ${Platform.operatingSystem}`',
    '',
    '## Summary',
    passed
        ? 'The fresh first-launch onboarding flow exposed the hosted setup path, rendered the hosted Repository/Branch labels plus helper copy, and allowed keyboard traversal through the hosted inputs.'
        : 'The fresh first-launch onboarding flow did not match the hosted onboarding UI contract. See the step results and exact error for the product-visible mismatch.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '',
      '```text',
      '${result['error'] ?? 'Unknown error'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# $_ticketKey regression: first-launch hosted onboarding does not match the hosted field visibility and keyboard flow',
    '',
    '## Summary',
    'The first-launch onboarding route for a fresh user does not satisfy the hosted setup expectations from $_ticketKey. The hosted flow was exercised through the production widget tree, but the observed visible labels, helper copy, field visibility, and/or keyboard traversal did not match the production hosted `Repository` + `Branch` onboarding contract.',
    '',
    '## Steps to reproduce',
    ..._bugReproLines(result),
    '',
    '## Actual result',
    _actualResult(result),
    '',
    '## Expected result',
    '${result['expected_result']}',
    '',
    '## Exact error message and stack trace',
    '```text',
    '${result['error'] ?? 'Unknown error'}',
    '',
    '${result['traceback'] ?? ''}',
    '```',
    '',
    '## Environment',
    '- URL/runtime: `flutter test` widget harness for the production `TrackStateApp` first-launch onboarding route',
    '- Browser: n/a',
    '- OS: `${Platform.operatingSystem}`',
    '- Viewport: `1440x960`',
    '- SharedPreferences seed: `{}` (no saved or migrated workspace profiles)',
    '- Run command: `$_runCommand`',
    '',
    '## Logs and observations',
    '',
    '### Initial visible texts',
    '```text',
    _formatList(_resultList(result['initial_visible_texts'])),
    '```',
    '',
    '### Hosted visible texts',
    '```text',
    _formatList(_resultList(result['hosted_visible_texts'])),
    '```',
    '',
    '### Hosted interactive semantics labels',
    '```text',
    _formatList(_resultList(result['hosted_interactive_semantics_labels'])),
    '```',
    '',
    '### Keyboard focus order',
    '```text',
    _formatList(_resultList(result['focus_order'])),
    '```',
    '',
    '### Screenshot',
    'No screenshot captured in this Flutter widget test run.',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps = _resultSteps(result);
  return steps
      .map(
        (step) =>
            '* Step ${step['step']} — ${step['status']}: '
            '${step['action']}\n'
            '**Observed:** {noformat}${step['observed']}{noformat}',
      )
      .toList(growable: false);
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks = _resultChecks(result);
  return checks
      .map(
        (entry) =>
            '* ${entry['check']}\n'
            '**Observed:** {noformat}${entry['observed']}{noformat}',
      )
      .toList(growable: false);
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = _resultSteps(result);
  return steps
      .map(
        (step) =>
            '- **Step ${step['step']} — ${step['status']}**: ${step['action']}\n'
            '  - Observed: '
            '`${step['observed']}`',
      )
      .toList(growable: false);
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks = _resultChecks(result);
  return checks
      .map(
        (entry) =>
            '- **${entry['check']}**\n'
            '  - Observed: '
            '`${entry['observed']}`',
      )
      .toList(growable: false);
}

List<String> _bugReproLines(Map<String, Object?> result) {
  final steps = _resultSteps(result);
  final lines = <String>[];
  for (final step in steps) {
    final status = '${step['status']}' == 'passed' ? '✅' : '❌';
    lines.add('${step['step']}. $status ${step['action']}');
    lines.add('   - Observed: ${step['observed']}');
  }
  return lines;
}

String _actualResult(Map<String, Object?> result) {
  final hostedVisibleTexts = _formatList(
    _resultList(result['hosted_visible_texts']),
  );
  final focusOrder = _formatList(_resultList(result['focus_order']));
  return 'After switching to Hosted repository, the production onboarding route showed: '
      '$hostedVisibleTexts. The recorded keyboard focus order was: $focusOrder.';
}

List<String> _missingExpectedTexts({
  required List<String> expected,
  required List<String> observed,
}) {
  return expected
      .where((text) => !observed.contains(text))
      .toList(growable: false);
}

List<Map<String, Object?>> _resultSteps(Map<String, Object?> result) {
  final raw = result['steps'];
  if (raw is List<Map<String, Object?>>) {
    return raw;
  }
  if (raw is List) {
    return raw
        .whereType<Map>()
        .map((entry) => entry.map((key, value) => MapEntry('$key', value)))
        .toList(growable: false);
  }
  return const <Map<String, Object?>>[];
}

List<Map<String, Object?>> _resultChecks(Map<String, Object?> result) {
  final raw = result['human_verification'];
  if (raw is List<Map<String, Object?>>) {
    return raw;
  }
  if (raw is List) {
    return raw
        .whereType<Map>()
        .map((entry) => entry.map((key, value) => MapEntry('$key', value)))
        .toList(growable: false);
  }
  return const <Map<String, Object?>>[];
}

List<String> _resultList(Object? value) {
  if (value is List<String>) {
    return value;
  }
  if (value is List) {
    return value.map((item) => '$item').toList(growable: false);
  }
  return const <String>[];
}

String _formatList(List<String> values) {
  if (values.isEmpty) {
    return '<none>';
  }
  return values.join(' | ');
}
