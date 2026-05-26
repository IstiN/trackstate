import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/workspace_onboarding_accessibility_screen.dart';
import '../../core/models/workspace_onboarding_contrast_observation.dart';
import '../../core/utils/theme_token_policy_probe.dart';
import '../../fixtures/workspace_onboarding_accessibility_screen_fixture.dart';

const String _ticketKey = 'TS-705';
const String _ticketSummary =
    'Onboarding UI accessibility — meaningful semantics and AA contrast compliance';
const String _testFilePath = 'testing/tests/TS-705/test_ts_705.dart';
const String _runCommand =
    'flutter test testing/tests/TS-705/test_ts_705.dart --reporter expanded';

const List<String> _requestSteps = <String>[
  'Open the Onboarding screen.',
  'Use a semantics debugger/screen reader to verify all interactive elements (segmented choices, inputs, buttons) have descriptive labels.',
  'Navigate the screen using only the keyboard (Tab/Shift+Tab).',
  'Verify text and icon contrast ratios (e.g., placeholder text vs input background).',
];

const List<String> _expectedLocalVisibleTexts = <String>[
  'Add workspace',
  'Choose a local folder or hosted repository to get started.',
  'Local folder',
  'Hosted repository',
  'Repository Path',
  'Enter the local Git folder path.',
  'Branch',
  'Open',
];

const List<String> _expectedHostedVisibleTexts = <String>[
  'Add workspace',
  'Choose a local folder or hosted repository to get started.',
  'Local folder',
  'Hosted repository',
  'Repository',
  'Enter the repository as owner/repo.',
  'Branch',
  'Connect GitHub in an existing hosted workspace to browse accessible repositories. You can still enter owner/repo manually here.',
  'Open',
];

const List<String> _expectedLocalInteractiveLabels = <String>[
  'Local folder',
  'Hosted repository',
  'Repository Path',
  'Branch',
  'Open',
];

const List<String> _expectedHostedInteractiveLabels = <String>[
  'Local folder',
  'Hosted repository',
  'Repository',
  'Branch',
  'Open',
];

const List<String> _expectedLocalFocusOrder = <String>[
  'Local folder',
  'Hosted repository',
  'Repository Path',
  'Branch',
  'Open',
];

const List<String> _expectedHostedFocusOrder = <String>[
  'Local folder',
  'Hosted repository',
  'Repository',
  'Branch',
  'Open',
];

void main() {
  testWidgets(
    'TS-705 onboarding screen exposes accessible semantics, logical keyboard order, and AA contrast',
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

      try {
        final screen = await launchWorkspaceOnboardingAccessibilityFixture(
          tester,
        );
        final failures = <String>[];

        final localVisibleTexts = await screen.visibleTexts(hosted: false);
        final hostedVisibleTexts = await screen.visibleTexts(hosted: true);
        result['local_visible_texts'] = localVisibleTexts;
        result['hosted_visible_texts'] = hostedVisibleTexts;

        final missingLocalVisibleTexts = _missingExpectedLabels(
          expected: _expectedLocalVisibleTexts,
          observed: localVisibleTexts,
        );
        final missingHostedVisibleTexts = _missingExpectedLabels(
          expected: _expectedHostedVisibleTexts,
          observed: hostedVisibleTexts,
        );

        if (missingLocalVisibleTexts.isNotEmpty ||
            missingHostedVisibleTexts.isNotEmpty) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action: _requestSteps[0],
            observed:
                'missing_local_texts=${missingLocalVisibleTexts.join(', ')}; '
                'local_visible_texts=${localVisibleTexts.join(' | ')}; '
                'missing_hosted_texts=${missingHostedVisibleTexts.join(', ')}; '
                'hosted_visible_texts=${hostedVisibleTexts.join(' | ')}',
          );
          failures.add(
            'Step 1 failed: the first-launch onboarding screen did not expose the ticket-required dual local-folder/hosted-repository onboarding flow.\n'
            'Missing local-mode texts: ${missingLocalVisibleTexts.join(', ')}\n'
            'Observed local-mode texts: ${localVisibleTexts.join(' | ')}\n'
            'Missing hosted-mode texts: ${missingHostedVisibleTexts.join(', ')}\n'
            'Observed hosted-mode texts: ${hostedVisibleTexts.join(' | ')}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action: _requestSteps[0],
            observed:
                'local_visible_texts=${localVisibleTexts.join(' | ')}; '
                'hosted_visible_texts=${hostedVisibleTexts.join(' | ')}',
          );
        }

        final localInteractiveLabels = await screen.interactiveSemanticsLabels(
          hosted: false,
        );
        final hostedInteractiveLabels = await screen.interactiveSemanticsLabels(
          hosted: true,
        );
        result['local_interactive_semantics_labels'] = localInteractiveLabels;
        result['hosted_interactive_semantics_labels'] = hostedInteractiveLabels;

        final missingLocalInteractiveLabels = _missingExpectedLabels(
          expected: _expectedLocalInteractiveLabels,
          observed: localInteractiveLabels,
        );
        final missingHostedInteractiveLabels = _missingExpectedLabels(
          expected: _expectedHostedInteractiveLabels,
          observed: hostedInteractiveLabels,
        );
        final emptyInteractiveLabels = <String>[
          ...localInteractiveLabels,
          ...hostedInteractiveLabels,
        ].where((label) => label.trim().isEmpty).toList(growable: false);
        final emptyInteractiveLabelsObserved = emptyInteractiveLabels.isEmpty
            ? '<none>'
            : emptyInteractiveLabels.join(', ');

        if (missingLocalInteractiveLabels.isNotEmpty ||
            missingHostedInteractiveLabels.isNotEmpty ||
            emptyInteractiveLabels.isNotEmpty) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: _requestSteps[1],
            observed:
                'local_labels=${localInteractiveLabels.join(' | ')}; '
                'missing_local_labels=${missingLocalInteractiveLabels.join(', ')}; '
                'hosted_labels=${hostedInteractiveLabels.join(' | ')}; '
                'missing_hosted_labels=${missingHostedInteractiveLabels.join(', ')}; '
                'empty_labels=$emptyInteractiveLabelsObserved',
          );
          failures.add(
            'Step 2 failed: the onboarding semantics did not expose the ticket-required descriptive labels across the local and hosted forms.\n'
            'Missing local-mode labels: ${missingLocalInteractiveLabels.join(', ')}\n'
            'Observed local-mode labels: ${localInteractiveLabels.join(' | ')}\n'
            'Missing hosted-mode labels: ${missingHostedInteractiveLabels.join(', ')}\n'
            'Observed hosted-mode labels: ${hostedInteractiveLabels.join(' | ')}\n'
            'Empty labels: $emptyInteractiveLabelsObserved',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action: _requestSteps[1],
            observed:
                'local_labels=${localInteractiveLabels.join(' | ')}; '
                'hosted_labels=${hostedInteractiveLabels.join(' | ')}',
          );
        }

        var localForwardFocusOrder = <String>[];
        var localBackwardFocusOrder = <String>[];
        var hostedForwardFocusOrder = <String>[];
        var hostedBackwardFocusOrder = <String>[];
        result['local_forward_focus_order'] = localForwardFocusOrder;
        result['local_backward_focus_order'] = localBackwardFocusOrder;
        result['hosted_forward_focus_order'] = hostedForwardFocusOrder;
        result['hosted_backward_focus_order'] = hostedBackwardFocusOrder;

        if (missingLocalVisibleTexts.isNotEmpty ||
            missingHostedVisibleTexts.isNotEmpty) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action: _requestSteps[2],
            observed:
                'ticket_required_keyboard_path_unavailable=true; '
                'local_visible_texts=${localVisibleTexts.join(' | ')}; '
                'hosted_visible_texts=${hostedVisibleTexts.join(' | ')}',
          );
          failures.add(
            'Step 3 failed: the ticket-required keyboard path could not be exercised because the first-launch onboarding screen did not render the required local and hosted onboarding controls.\n'
            'Observed local-mode texts: ${localVisibleTexts.join(' | ')}\n'
            'Observed hosted-mode texts: ${hostedVisibleTexts.join(' | ')}',
          );
        } else {
          localForwardFocusOrder = await screen.collectForwardFocusOrder(
            hosted: false,
          );
          localBackwardFocusOrder = await screen.collectBackwardFocusOrder(
            hosted: false,
          );
          hostedForwardFocusOrder = await screen.collectForwardFocusOrder(
            hosted: true,
          );
          hostedBackwardFocusOrder = await screen.collectBackwardFocusOrder(
            hosted: true,
          );
          result['local_forward_focus_order'] = localForwardFocusOrder;
          result['local_backward_focus_order'] = localBackwardFocusOrder;
          result['hosted_forward_focus_order'] = hostedForwardFocusOrder;
          result['hosted_backward_focus_order'] = hostedBackwardFocusOrder;

          final focusFailures = <String>[];
          if (!_sameOrder(localForwardFocusOrder, _expectedLocalFocusOrder)) {
            focusFailures.add(
              'Expected local forward: ${_expectedLocalFocusOrder.join(' -> ')}\n'
              'Observed local forward: ${localForwardFocusOrder.join(' -> ')}',
            );
          }
          if (!_sameOrder(
            localBackwardFocusOrder,
            _expectedLocalFocusOrder.reversed.toList(),
          )) {
            focusFailures.add(
              'Expected local backward: ${_expectedLocalFocusOrder.reversed.join(' -> ')}\n'
              'Observed local backward: ${localBackwardFocusOrder.join(' -> ')}',
            );
          }
          if (!_sameOrder(hostedForwardFocusOrder, _expectedHostedFocusOrder)) {
            focusFailures.add(
              'Expected hosted forward: ${_expectedHostedFocusOrder.join(' -> ')}\n'
              'Observed hosted forward: ${hostedForwardFocusOrder.join(' -> ')}',
            );
          }
          if (!_sameOrder(
            hostedBackwardFocusOrder,
            _expectedHostedFocusOrder.reversed.toList(),
          )) {
            focusFailures.add(
              'Expected hosted backward: ${_expectedHostedFocusOrder.reversed.join(' -> ')}\n'
              'Observed hosted backward: ${hostedBackwardFocusOrder.join(' -> ')}',
            );
          }

          if (focusFailures.isNotEmpty) {
            _recordStep(
              result,
              step: 3,
              status: 'failed',
              action: _requestSteps[2],
              observed:
                  'local_forward=${localForwardFocusOrder.join(' -> ')}; '
                  'local_backward=${localBackwardFocusOrder.join(' -> ')}; '
                  'hosted_forward=${hostedForwardFocusOrder.join(' -> ')}; '
                  'hosted_backward=${hostedBackwardFocusOrder.join(' -> ')}',
            );
            failures.add(
              'Step 3 failed: keyboard traversal on the onboarding screen did not stay in the ticket-required logical order.\n${focusFailures.join('\n')}',
            );
          } else {
            _recordStep(
              result,
              step: 3,
              status: 'passed',
              action: _requestSteps[2],
              observed:
                  'local_forward=${localForwardFocusOrder.join(' -> ')}; '
                  'local_backward=${localBackwardFocusOrder.join(' -> ')}; '
                  'hosted_forward=${hostedForwardFocusOrder.join(' -> ')}; '
                  'hosted_backward=${hostedBackwardFocusOrder.join(' -> ')}',
            );
          }
        }

        final localContrast = await screen.observeContrastSet(hosted: false);
        final hostedContrast = await screen.observeContrastSet(hosted: true);
        final placeholderVisible =
            await screen.hasVisiblePlaceholderText(hosted: false) ||
            await screen.hasVisiblePlaceholderText(hosted: true);
        final iconVisible =
            await screen.hasVisibleIcons(hosted: false) ||
            await screen.hasVisibleIcons(hosted: true);
        final tokenCheck = await _runThemeTokenCheck();
        result['local_contrast'] = localContrast.map(_contrastAsMap).toList();
        result['hosted_contrast'] = hostedContrast.map(_contrastAsMap).toList();
        result['placeholder_text_visible'] = placeholderVisible;
        result['icon_visible'] = iconVisible;
        result['theme_token_check'] = tokenCheck;

        final failingContrast = <WorkspaceOnboardingContrastObservation>[
          ...localContrast,
          ...hostedContrast,
        ].where((observation) => !observation.passes).toList(growable: false);
        if (failingContrast.isNotEmpty ||
            tokenCheck['exit_code'] != 0 ||
            (tokenCheck['output'] != null &&
                '${tokenCheck['output']}'.contains('warning •'))) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action: _requestSteps[3],
            observed:
                'local_contrast=${localContrast.join(' || ')}; '
                'hosted_contrast=${hostedContrast.join(' || ')}; '
                'placeholder_visible=$placeholderVisible; '
                'icon_visible=$iconVisible; '
                'theme_token_exit=${tokenCheck['exit_code']}; '
                'theme_token_output=${_singleLine(tokenCheck['output'])}',
          );
          failures.add(
            'Step 4 failed: the onboarding screen did not satisfy the requested contrast/token expectations.\n'
            'Failing contrast observations: ${failingContrast.join(' || ')}\n'
            'Visible placeholder text present: $placeholderVisible\n'
            'Visible icons present: $iconVisible\n'
            'Theme token check exit code: ${tokenCheck['exit_code']}\n'
            'Theme token output:\n${tokenCheck['output']}',
          );
        } else {
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action: _requestSteps[3],
            observed:
                'local_contrast=${localContrast.join(' || ')}; '
                'hosted_contrast=${hostedContrast.join(' || ')}; '
                'placeholder_visible=$placeholderVisible; '
                'icon_visible=$iconVisible; '
                'theme_token_output=${_singleLine(tokenCheck['output'])}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the first-launch onboarding screen exactly as a user would see it before any workspace is saved, in both the local-folder and hosted-repository modes.',
          observed:
              'local_visible_texts=${localVisibleTexts.join(' | ')}; '
              'hosted_visible_texts=${hostedVisibleTexts.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the visible controls and semantics labels users interact with in each mode: segmented choices, form fields, and the Open action.',
          observed:
              'local_labels=${localInteractiveLabels.join(' | ')}; '
              'hosted_labels=${hostedInteractiveLabels.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the keyboard experience from a user perspective by tabbing forward and backward through both onboarding modes.',
          observed:
              localForwardFocusOrder.isEmpty &&
                  localBackwardFocusOrder.isEmpty &&
                  hostedForwardFocusOrder.isEmpty &&
                  hostedBackwardFocusOrder.isEmpty
              ? 'ticket_required_keyboard_path_unavailable=true; '
                    'local_visible_texts=${localVisibleTexts.join(' | ')}; '
                    'hosted_visible_texts=${hostedVisibleTexts.join(' | ')}'
              : 'local_forward=${localForwardFocusOrder.join(' -> ')}; '
                    'local_backward=${localBackwardFocusOrder.join(' -> ')}; '
                    'hosted_forward=${hostedForwardFocusOrder.join(' -> ')}; '
                    'hosted_backward=${hostedBackwardFocusOrder.join(' -> ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the rendered low-emphasis onboarding text and selected controls users actually see in both modes, and verified the AC4 theme-token policy output.',
          observed:
              'placeholder_visible=$placeholderVisible; '
              'icon_visible=$iconVisible; '
              'local_contrast=${localContrast.join(' || ')}; '
              'hosted_contrast=${hostedContrast.join(' || ')}',
        );

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

Future<Map<String, Object?>> _runThemeTokenCheck() async {
  return runThemeTokenPolicyCheck(<String>[
    'lib/ui/features/tracker/views/trackstate_app.dart',
  ]);
}

List<String> _missingExpectedLabels({
  required List<String> expected,
  required List<String> observed,
}) {
  return expected
      .where((label) => !observed.any((candidate) => candidate.contains(label)))
      .toList(growable: false);
}

bool _sameOrder(List<String> left, List<String> right) {
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

Map<String, Object?> _contrastAsMap(
  WorkspaceOnboardingContrastObservation observation,
) {
  return <String, Object?>{
    'label': observation.label,
    'text': observation.text,
    'foreground_hex': observation.foregroundHex,
    'background_hex': observation.backgroundHex,
    'contrast_ratio': observation.contrastRatio,
    'minimum_contrast': observation.minimumContrast,
    'passes': observation.passes,
  };
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
    '* Opened the production first-launch onboarding screen with no saved workspace profiles.',
    '* Checked the local-folder onboarding mode for the required heading, segmented choices, form fields, helper copy, and Open action.',
    '* Switched to the hosted-repository onboarding mode and checked the required heading, segmented choices, form fields, helper copy, hosted hint, and Open action.',
    '* Inspected the semantics labels exposed for segmented choices, text inputs, and the Open action in both modes.',
    '* Tabbed forward and backward through both onboarding modes to confirm logical keyboard focus order.',
    '* Checked rendered contrast for the visible heading, subtitle, selected mode control, helper text, Open action, and ran the repository theme-token policy command against {noformat}lib/ui/features/tracker/views/trackstate_app.dart{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: first-launch onboarding exposed both local-folder and hosted-repository paths, surfaced descriptive semantics, kept keyboard traversal logical in both modes, met the requested contrast thresholds, and passed the AC4 theme-token policy gate.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Placeholder text visible: {noformat}${result['placeholder_text_visible']}{noformat}',
    '* Icons visible: {noformat}${result['icon_visible']}{noformat}',
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

  final tokenCheck = result['theme_token_check'];
  if (tokenCheck is Map<String, Object?>) {
    lines.addAll(<String>[
      '',
      'h4. Theme token policy output',
      '{code}',
      '${tokenCheck['output'] ?? '<missing>'}',
      '{code}',
    ]);
  }

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
    '- Opened the production first-launch onboarding screen with no saved workspace profiles.',
    '- Checked the local-folder onboarding mode for the required heading, segmented choices, form fields, helper copy, and Open action.',
    '- Switched to the hosted-repository onboarding mode and checked the required heading, segmented choices, form fields, helper copy, hosted hint, and Open action.',
    '- Inspected the semantics labels exposed for segmented choices, text inputs, and the Open action in both modes.',
    '- Tabbed forward and backward through both onboarding modes to confirm logical keyboard focus order.',
    '- Checked rendered contrast for the visible heading, subtitle, selected mode control, helper text, Open action, and ran the repository theme-token policy command against `lib/ui/features/tracker/views/trackstate_app.dart`.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: first-launch onboarding exposed both local-folder and hosted-repository paths, surfaced descriptive semantics, kept keyboard traversal logical in both modes, met the requested contrast thresholds, and passed the AC4 theme-token policy gate.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
    '- Placeholder text visible: `${result['placeholder_text_visible']}`',
    '- Icons visible: `${result['icon_visible']}`',
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

  final tokenCheck = result['theme_token_check'];
  if (tokenCheck is Map<String, Object?>) {
    lines.addAll(<String>[
      '',
      '### Theme token policy output',
      '```',
      '${tokenCheck['output'] ?? '<missing>'}',
      '```',
    ]);
  }

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
    '# TS-705',
    '',
    '- Status: $statusLabel',
    '- Test case: $_ticketSummary',
    '- Run command: `$_runCommand`',
    '- Environment: `flutter test` on `${Platform.operatingSystem}`',
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
  final localVisibleTexts =
      ((result['local_visible_texts'] as List?) ?? const []).join(' | ');
  final hostedVisibleTexts =
      ((result['hosted_visible_texts'] as List?) ?? const []).join(' | ');
  final localLabels =
      ((result['local_interactive_semantics_labels'] as List?) ?? const [])
          .join(' | ');
  final hostedLabels =
      ((result['hosted_interactive_semantics_labels'] as List?) ?? const [])
          .join(' | ');
  final localForward = _joinedOrUnavailable(
    result['local_forward_focus_order'] as List?,
  );
  final localBackward = _joinedOrUnavailable(
    result['local_backward_focus_order'] as List?,
  );
  final hostedForward = _joinedOrUnavailable(
    result['hosted_forward_focus_order'] as List?,
  );
  final hostedBackward = _joinedOrUnavailable(
    result['hosted_backward_focus_order'] as List?,
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
    '4. ${_requestSteps[3]}',
    '   - ${_stepOutcome(result, 4)}',
    '',
    '## Actual vs Expected',
    '- **Expected:** With no saved workspace profiles, the first-launch onboarding screen should expose `Local folder` and `Hosted repository` as equal first-class choices, show the local `Repository Path` / `Branch` form, switch to the hosted `Repository` / `Branch` form with the hosted helper text, expose descriptive semantics for those controls, keep keyboard traversal logical in both directions, and meet the requested contrast thresholds without theme-token warnings.',
    '- **Actual:** `${localVisibleTexts}` was rendered in local mode and `${hostedVisibleTexts}` was rendered after attempting to switch to hosted mode. The required dual-choice onboarding copy, semantics labels, and keyboard path were not fully available. Local labels: `${localLabels}`. Hosted labels: `${hostedLabels}`. Local keyboard order: `${localForward}` / `${localBackward}`. Hosted keyboard order: `${hostedForward}` / `${hostedBackward}`.',
    '',
    '## Exact error message / stack trace',
    '```',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Environment',
    '- Command: `$_runCommand`',
    '- OS: `${Platform.operatingSystem}`',
    '- Runtime: `flutter test`',
    '- Repository path: `${Directory.current.path}`',
    '- Viewport: `1440x900`',
    '- Placeholder text visible: `${result['placeholder_text_visible']}`',
    '- Icons visible: `${result['icon_visible']}`',
    '',
    '## Relevant logs',
    '```',
    'Local visible texts: $localVisibleTexts',
    'Hosted visible texts: $hostedVisibleTexts',
    'Local semantics labels: $localLabels',
    'Hosted semantics labels: $hostedLabels',
    'Local forward focus: $localForward',
    'Local backward focus: $localBackward',
    'Hosted forward focus: $hostedForward',
    'Hosted backward focus: $hostedBackward',
    'Theme token check: ${_singleLine((result['theme_token_check'] as Map?)?['output'])}',
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

String _singleLine(Object? value) {
  return '${value ?? ''}'.replaceAll('\n', ' ').trim();
}

String _joinedOrUnavailable(List? values) {
  final items = (values ?? const <Object?>[]).whereType<Object?>().toList();
  if (items.isEmpty) {
    return '<unavailable>';
  }
  return items.join(' -> ');
}
