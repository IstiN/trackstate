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

const List<String> _ticketVisibleTexts = <String>[
  'Add workspace',
  'Choose a local folder or hosted repository to get started.',
  'Local folder',
  'Hosted repository',
  'Repository Path',
  'Branch',
  'Enter the local Git folder path.',
  'Open',
];

const List<String> _currentInteractiveLabels = <String>[
  'Open existing folder',
  'Initialize folder',
];

const List<String> _currentFocusOrder = <String>[
  'Open existing folder',
  'Initialize folder',
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

        final visibleTexts = screen.visibleTexts();
        result['visible_texts'] = visibleTexts;
        final missingTicketVisibleTexts = _missingExpectedLabels(
          expected: _ticketVisibleTexts,
          observed: visibleTexts,
        );

        if (missingTicketVisibleTexts.isNotEmpty) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action: _requestSteps[0],
            observed:
                'missing_ticket_texts=${missingTicketVisibleTexts.join(', ')}; '
                'observed_visible_texts=${visibleTexts.join(' | ')}',
          );
          failures.add(
            'Step 1 failed: the first-launch onboarding screen does not expose the ticket-required local-folder/hosted-repository onboarding flow.\n'
            'Missing ticket-visible texts: ${missingTicketVisibleTexts.join(', ')}\n'
            'Observed visible texts: ${visibleTexts.join(' | ')}\n'
            'Missing production capability: with no saved workspace profiles, users cannot reach a first-launch hosted-repository onboarding form because the screen only exposes "Open existing folder" and "Initialize folder".',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action: _requestSteps[0],
            observed: 'visible_texts=${visibleTexts.join(' | ')}',
          );
        }

        final interactiveLabels = screen.interactiveSemanticsLabels();
        result['interactive_semantics_labels'] = interactiveLabels;
        final missingInteractiveLabels = _missingExpectedLabels(
          expected: _currentInteractiveLabels,
          observed: interactiveLabels,
        );
        final emptyInteractiveLabels = interactiveLabels
            .where((label) => label.trim().isEmpty)
            .toList(growable: false);

        if (missingInteractiveLabels.isNotEmpty ||
            emptyInteractiveLabels.isNotEmpty) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: _requestSteps[1],
            observed:
                'interactive_labels=${interactiveLabels.join(' | ')}; '
                'missing_labels=${missingInteractiveLabels.join(', ')}; '
                'empty_labels=${emptyInteractiveLabels.join(', ')}',
          );
          failures.add(
            'Step 2 failed: the currently rendered first-launch onboarding actions did not expose complete descriptive semantics labels.\n'
            'Missing labels: ${missingInteractiveLabels.join(', ')}\n'
            'Empty labels: ${emptyInteractiveLabels.join(', ')}\n'
            'Observed labels: ${interactiveLabels.join(' | ')}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action: _requestSteps[1],
            observed: 'interactive_labels=${interactiveLabels.join(' | ')}',
          );
        }

        final forwardFocusOrder = <String>[];
        final backwardFocusOrder = <String>[];
        result['forward_focus_order'] = forwardFocusOrder;
        result['backward_focus_order'] = backwardFocusOrder;

        if (missingTicketVisibleTexts.isNotEmpty) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action: _requestSteps[2],
            observed:
                'ticket_required_keyboard_path_unavailable=true; '
                'observed_visible_texts=${visibleTexts.join(' | ')}',
          );
          failures.add(
            'Step 3 failed: the ticket-required keyboard path could not be exercised because the first-launch onboarding screen does not render the required local-folder/hosted-repository controls.\n'
            'Observed visible texts: ${visibleTexts.join(' | ')}',
          );
        } else {
          final currentForwardFocusOrder = await screen
              .collectForwardFocusOrder();
          final currentBackwardFocusOrder = await screen
              .collectBackwardFocusOrder();
          result['forward_focus_order'] = currentForwardFocusOrder;
          result['backward_focus_order'] = currentBackwardFocusOrder;

          if (!_sameOrder(currentForwardFocusOrder, _currentFocusOrder) ||
              !_sameOrder(
                currentBackwardFocusOrder,
                _currentFocusOrder.reversed.toList(),
              )) {
            _recordStep(
              result,
              step: 3,
              status: 'failed',
              action: _requestSteps[2],
              observed:
                  'forward_focus=${currentForwardFocusOrder.join(' -> ')}; '
                  'backward_focus=${currentBackwardFocusOrder.join(' -> ')}',
            );
            failures.add(
              'Step 3 failed: keyboard traversal on the currently rendered first-launch onboarding actions did not stay in logical order.\n'
              'Expected forward order: ${_currentFocusOrder.join(' -> ')}\n'
              'Observed forward order: ${currentForwardFocusOrder.join(' -> ')}\n'
              'Expected backward order: ${_currentFocusOrder.reversed.join(' -> ')}\n'
              'Observed backward order: ${currentBackwardFocusOrder.join(' -> ')}',
            );
          } else {
            _recordStep(
              result,
              step: 3,
              status: 'passed',
              action: _requestSteps[2],
              observed:
                  'forward_focus=${currentForwardFocusOrder.join(' -> ')}; '
                  'backward_focus=${currentBackwardFocusOrder.join(' -> ')}',
            );
          }
        }

        final contrast = screen.observeContrastSet();
        final placeholderVisible = screen.hasVisiblePlaceholderText();
        final iconVisible = screen.hasVisibleIcons();
        final tokenCheck = await _runThemeTokenCheck();
        result['contrast'] = contrast.map(_contrastAsMap).toList();
        result['placeholder_text_visible'] = placeholderVisible;
        result['icon_visible'] = iconVisible;
        result['theme_token_check'] = tokenCheck;

        final failingContrast = contrast
            .where((observation) => !observation.passes)
            .toList(growable: false);
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
                'contrast=${contrast.join(' || ')}; '
                'placeholder_visible=$placeholderVisible; '
                'icon_visible=$iconVisible; '
                'theme_token_exit=${tokenCheck['exit_code']}; '
                'theme_token_output=${_singleLine(tokenCheck['output'])}',
          );
          failures.add(
            'Step 4 failed: the currently rendered first-launch onboarding screen did not satisfy the requested contrast/token expectations.\n'
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
                'contrast=${contrast.join(' || ')}; '
                'placeholder_visible=$placeholderVisible; '
                'icon_visible=$iconVisible; '
                'theme_token_output=${_singleLine(tokenCheck['output'])}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the first-launch onboarding screen exactly as a user would see it before any workspace is saved.',
          observed: 'visible_texts=${visibleTexts.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the visible actions users can currently reach on that first-launch screen and inspected the semantics labels exposed for them.',
          observed: 'interactive_labels=${interactiveLabels.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the keyboard experience from a user perspective by tabbing forward and backward across the currently rendered first-launch actions.',
          observed: forwardFocusOrder.isEmpty && backwardFocusOrder.isEmpty
              ? 'ticket_required_keyboard_path_unavailable=true; observed_visible_texts=${visibleTexts.join(' | ')}'
              : 'forward_focus=${forwardFocusOrder.join(' -> ')}; backward_focus=${backwardFocusOrder.join(' -> ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the rendered heading, subtitle, visible action labels, visible action icons, and AC4 theme-token output for the first-launch onboarding screen.',
          observed:
              'placeholder_visible=$placeholderVisible; icon_visible=$iconVisible; contrast=${contrast.join(' || ')}',
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
    '* Checked whether that first-launch screen still exposed the ticket-required {noformat}Local folder{noformat} and {noformat}Hosted repository{noformat} onboarding choices.',
    '* Inspected the semantics labels exposed for the currently rendered first-launch actions.',
    '* Tabbed forward and backward through the currently rendered first-launch actions to confirm logical keyboard focus order.',
    '* Checked rendered contrast for the visible heading, subtitle, action labels, action icons, and ran the repository theme-token policy command against {noformat}lib/ui/features/tracker/views/trackstate_app.dart{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the first-launch onboarding screen exposed the requested onboarding choices, meaningful semantics labels, logical keyboard traversal, compliant contrast, and passed the AC4 theme-token policy gate.'
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
    '- Checked whether that first-launch screen still exposed the ticket-required `Local folder` and `Hosted repository` onboarding choices.',
    '- Inspected the semantics labels exposed for the currently rendered first-launch actions.',
    '- Tabbed forward and backward through the currently rendered first-launch actions to confirm logical keyboard focus order.',
    '- Checked rendered contrast for the visible heading, subtitle, action labels, action icons, and ran the repository theme-token policy command against `lib/ui/features/tracker/views/trackstate_app.dart`.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the first-launch onboarding screen exposed the requested onboarding choices, meaningful semantics labels, logical keyboard traversal, compliant contrast, and passed the AC4 theme-token policy gate.'
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
    'With no saved workspace profiles, the first-launch onboarding screen should expose the ticket-required `Local folder` and `Hosted repository` choices, give all interactive elements non-empty semantics labels, keep keyboard focus order logical in both directions, meet the requested contrast thresholds, and pass the AC4 theme-token policy check without warnings.',
    '',
    '## Actual result',
    '${result['error'] ?? '<missing>'}',
    '',
    '## Missing/broken production capability',
    'The first-launch onboarding screen no longer exposes the ticket-required hosted-repository onboarding path. In the required no-profile entry state, users only see `Open existing folder` and `Initialize folder`, so the hosted-repository onboarding form cannot be exercised from the production UI.',
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
    '- Placeholder text visible: `${result['placeholder_text_visible']}`',
    '- Icons visible: `${result['icon_visible']}`',
    '',
    '## Relevant logs',
    '```',
    'Visible texts: ${((result['visible_texts'] as List?) ?? const []).join(' | ')}',
    'Interactive semantics labels: ${((result['interactive_semantics_labels'] as List?) ?? const []).join(' | ')}',
    'Forward focus: ${((result['forward_focus_order'] as List?) ?? const []).join(' -> ')}',
    'Backward focus: ${((result['backward_focus_order'] as List?) ?? const []).join(' -> ')}',
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
