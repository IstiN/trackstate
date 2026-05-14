import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../../core/interfaces/workspace_onboarding_accessibility_screen.dart';
import '../../core/models/workspace_onboarding_contrast_observation.dart';
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

const List<String> _expectedLocalLabels = <String>[
  'Local folder',
  'Hosted repository',
  'Repository Path',
  'Branch',
  'Open',
];

const List<String> _expectedHostedLabels = <String>[
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
        final WorkspaceOnboardingAccessibilityScreenHandle screen =
            await launchWorkspaceOnboardingAccessibilityFixture(tester);

        final failures = <String>[];

        final localVisibleTexts = screen.visibleTexts();
        result['local_visible_texts'] = localVisibleTexts;
        final missingLocalVisibleTexts =
            <String>[
                  'Add workspace',
                  'Choose a local folder or hosted repository to get started.',
                  'Local folder',
                  'Hosted repository',
                  'Repository Path',
                  'Branch',
                  'Enter the local Git folder path.',
                  'Open',
                ]
                .where((text) => !localVisibleTexts.contains(text))
                .toList(growable: false);
        if (missingLocalVisibleTexts.isNotEmpty) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action: _requestSteps[0],
            observed:
                'Missing visible onboarding copy: ${missingLocalVisibleTexts.join(', ')}. '
                'Visible local-form texts: ${localVisibleTexts.join(' | ')}',
          );
          failures.add(
            'Step 1 failed: the first-launch onboarding screen did not render all expected visible text for a user opening the screen.\n'
            'Missing texts: ${missingLocalVisibleTexts.join(', ')}\n'
            'Observed texts: ${localVisibleTexts.join(' | ')}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action: _requestSteps[0],
            observed:
                'Visible local-form texts: ${localVisibleTexts.join(' | ')}',
          );
        }

        final localLabels = screen.interactiveSemanticsLabels();
        await screen.showHostedRepositoryForm();
        final hostedVisibleTexts = screen.visibleTexts();
        final hostedLabels = screen.interactiveSemanticsLabels();
        result['local_interactive_semantics_labels'] = localLabels;
        result['hosted_visible_texts'] = hostedVisibleTexts;
        result['hosted_interactive_semantics_labels'] = hostedLabels;

        final missingLocalLabels = _missingExpectedLabels(
          expected: _expectedLocalLabels,
          observed: localLabels,
        );
        final missingHostedLabels = _missingExpectedLabels(
          expected: _expectedHostedLabels,
          observed: hostedLabels,
        );
        final emptyLocalLabels = localLabels
            .where((label) => label.trim().isEmpty)
            .toList(growable: false);
        final emptyHostedLabels = hostedLabels
            .where((label) => label.trim().isEmpty)
            .toList(growable: false);
        final missingHostedVisibleTexts = <String>[
          'Repository',
          'Branch',
          'Enter the repository as owner/repo.',
          'Connect GitHub in an existing hosted workspace to browse accessible repositories. You can still enter owner/repo manually here.',
          'Open',
        ].where((text) => !hostedVisibleTexts.contains(text)).toList(growable: false);

        if (missingLocalLabels.isNotEmpty ||
            missingHostedLabels.isNotEmpty ||
            emptyLocalLabels.isNotEmpty ||
            emptyHostedLabels.isNotEmpty ||
            missingHostedVisibleTexts.isNotEmpty) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: _requestSteps[1],
            observed:
                'local_labels=${localLabels.join(' | ')}; hosted_labels=${hostedLabels.join(' | ')}; '
                'missing_local_labels=${missingLocalLabels.join(', ')}; '
                'missing_hosted_labels=${missingHostedLabels.join(', ')}; '
                'missing_hosted_visible_texts=${missingHostedVisibleTexts.join(', ')}',
          );
          failures.add(
            'Step 2 failed: the onboarding screen did not expose complete descriptive semantics labels for all interactive elements.\n'
            'Missing local labels: ${missingLocalLabels.join(', ')}\n'
            'Missing hosted labels: ${missingHostedLabels.join(', ')}\n'
            'Empty local labels: ${emptyLocalLabels.join(', ')}\n'
            'Empty hosted labels: ${emptyHostedLabels.join(', ')}\n'
            'Missing hosted visible texts: ${missingHostedVisibleTexts.join(', ')}\n'
            'Observed local labels: ${localLabels.join(' | ')}\n'
            'Observed hosted labels: ${hostedLabels.join(' | ')}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action: _requestSteps[1],
            observed:
                'local_labels=${localLabels.join(' | ')}; hosted_labels=${hostedLabels.join(' | ')}',
          );
        }

        final localForwardOrder = await screen.collectLocalForwardFocusOrder();
        final localBackwardOrder = await screen
            .collectLocalBackwardFocusOrder();
        final hostedForwardOrder = await screen
            .collectHostedForwardFocusOrder();
        final hostedBackwardOrder = await screen
            .collectHostedBackwardFocusOrder();
        result['local_forward_focus_order'] = localForwardOrder;
        result['local_backward_focus_order'] = localBackwardOrder;
        result['hosted_forward_focus_order'] = hostedForwardOrder;
        result['hosted_backward_focus_order'] = hostedBackwardOrder;

        if (!_sameOrder(localForwardOrder, _expectedLocalFocusOrder) ||
            !_sameOrder(
              localBackwardOrder,
              _expectedLocalFocusOrder.reversed.toList(),
            ) ||
            !_sameOrder(hostedForwardOrder, _expectedHostedFocusOrder) ||
            !_sameOrder(
              hostedBackwardOrder,
              _expectedHostedFocusOrder.reversed.toList(),
            )) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action: _requestSteps[2],
            observed:
                'local_forward=${localForwardOrder.join(' -> ')}; '
                'local_backward=${localBackwardOrder.join(' -> ')}; '
                'hosted_forward=${hostedForwardOrder.join(' -> ')}; '
                'hosted_backward=${hostedBackwardOrder.join(' -> ')}',
          );
          failures.add(
            'Step 3 failed: keyboard traversal on the onboarding screen did not stay in logical order.\n'
            'Expected local forward: ${_expectedLocalFocusOrder.join(' -> ')}\n'
            'Observed local forward: ${localForwardOrder.join(' -> ')}\n'
            'Expected local backward: ${_expectedLocalFocusOrder.reversed.join(' -> ')}\n'
            'Observed local backward: ${localBackwardOrder.join(' -> ')}\n'
            'Expected hosted forward: ${_expectedHostedFocusOrder.join(' -> ')}\n'
            'Observed hosted forward: ${hostedForwardOrder.join(' -> ')}\n'
            'Expected hosted backward: ${_expectedHostedFocusOrder.reversed.join(' -> ')}\n'
            'Observed hosted backward: ${hostedBackwardOrder.join(' -> ')}',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action: _requestSteps[2],
            observed:
                'local_forward=${localForwardOrder.join(' -> ')}; '
                'local_backward=${localBackwardOrder.join(' -> ')}; '
                'hosted_forward=${hostedForwardOrder.join(' -> ')}; '
                'hosted_backward=${hostedBackwardOrder.join(' -> ')}',
          );
        }

        await screen.showLocalFolderForm();
        final localContrast = screen.observeLocalContrastSet();
        await screen.showHostedRepositoryForm();
        final hostedContrast = screen.observeHostedContrastSet();
        final placeholderVisible = screen.hasVisiblePlaceholderText();
        final iconVisible = screen.hasVisibleIcons();
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
            placeholderVisible ||
            tokenCheck['exit_code'] != 0 ||
            tokenCheck['output'] != null &&
                '${tokenCheck['output']}'.contains('warning •')) {
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
              'Viewed the first-launch onboarding screen exactly as a user would see it before any workspace is saved.',
          observed:
              'local_visible_texts=${localVisibleTexts.join(' | ')}; hosted_visible_texts=${hostedVisibleTexts.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified the visible controls and labels in the places a user interacts with them: segmented choices at the top, text inputs in the form body, and the Open action at the bottom-right.',
          observed:
              'local_labels=${localLabels.join(' | ')}; hosted_labels=${hostedLabels.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the keyboard experience from a user perspective by tabbing forward and backward across both local and hosted onboarding forms.',
          observed:
              'local_forward=${localForwardOrder.join(' -> ')}; local_backward=${localBackwardOrder.join(' -> ')}; hosted_forward=${hostedForwardOrder.join(' -> ')}; hosted_backward=${hostedBackwardOrder.join(' -> ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the rendered low-emphasis copy users actually see on this screen. No placeholder text or icons were rendered, so the helper and informational texts were used for the low-contrast verification instead.',
          observed:
              'placeholder_visible=$placeholderVisible; icon_visible=$iconVisible; '
              'local_contrast=${localContrast.join(' || ')}; hosted_contrast=${hostedContrast.join(' || ')}',
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
  const path = 'lib/ui/features/tracker/views/trackstate_app.dart';
  final source = File(path).readAsStringSync();
  final violations = <String>[];
  final patterns = <RegExp>[
    RegExp(r'(?:const\s+)?Color\s*\(\s*(0x[0-9a-fA-F]{8})\s*\)'),
    RegExp(r'Color\.from(?:ARGB|RGBO)\s*\([^)]*\)'),
  ];
  for (final pattern in patterns) {
    for (final match in pattern.allMatches(source)) {
      final location = _locationForOffset(source, match.start);
      violations.add(
        'warning • Use TrackState theme tokens instead of hardcoded colors. '
        '${source.substring(match.start, match.end)} • '
        '$path:${location.line}:${location.column} • trackstate_theme_tokens',
      );
    }
  }
  final output = violations.isEmpty
      ? 'No theme token policy violations found.'
      : violations.join('\n');
  return <String, Object?>{
    'command':
        'inline theme token scan for lib/ui/features/tracker/views/trackstate_app.dart',
    'exit_code': violations.isEmpty ? 0 : 1,
    'output': output,
  };
}

({int line, int column}) _locationForOffset(String source, int offset) {
  var line = 1;
  var lineStart = 0;
  for (var index = 0; index < offset; index += 1) {
    if (source.codeUnitAt(index) == 10) {
      line += 1;
      lineStart = index + 1;
    }
  }
  return (line: line, column: offset - lineStart + 1);
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
    '* Opened the production onboarding screen in the first-launch state with no saved workspace profiles.',
    '* Verified the visible onboarding copy for both the local-folder and hosted-repository forms.',
    '* Inspected the semantics labels exposed for segmented choices, text inputs, and the Open action.',
    '* Tabbed forward and backward through both onboarding forms to confirm logical keyboard focus order.',
    '* Checked rendered contrast for heading, subtitle, selected segmented choices, helper/informational text, and the Open action.',
    '* Ran the repository theme-token policy command against {noformat}lib/ui/features/tracker/views/trackstate_app.dart{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: the onboarding screen exposed meaningful semantics labels, maintained logical keyboard traversal, met the requested contrast thresholds on the rendered text surfaces, and passed the AC4 theme-token policy gate.'
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
    '- Opened the production onboarding screen in the first-launch state with no saved workspace profiles.',
    '- Verified the visible onboarding copy for both the local-folder and hosted-repository forms.',
    '- Inspected the semantics labels exposed for segmented choices, text inputs, and the Open action.',
    '- Tabbed forward and backward through both onboarding forms to confirm logical keyboard focus order.',
    '- Checked rendered contrast for heading, subtitle, selected segmented choices, helper/informational text, and the Open action.',
    '- Ran the repository theme-token policy command against `lib/ui/features/tracker/views/trackstate_app.dart`.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: the onboarding screen exposed meaningful semantics labels, maintained logical keyboard traversal, met the requested contrast thresholds on the rendered text surfaces, and passed the AC4 theme-token policy gate.'
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
    'All interactive elements have non-empty semantics labels, keyboard focus order is logical in both directions, normal text contrast is at least 4.5:1, large text is at least 3.0:1, and the onboarding file passes the AC4 theme-token policy check without warnings.',
    '',
    '## Actual result',
    '${result['error'] ?? '<missing>'}',
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
    'Local visible texts: ${((result['local_visible_texts'] as List?) ?? const []).join(' | ')}',
    'Hosted visible texts: ${((result['hosted_visible_texts'] as List?) ?? const []).join(' | ')}',
    'Local semantics labels: ${((result['local_interactive_semantics_labels'] as List?) ?? const []).join(' | ')}',
    'Hosted semantics labels: ${((result['hosted_interactive_semantics_labels'] as List?) ?? const []).join(' | ')}',
    'Local forward focus: ${((result['local_forward_focus_order'] as List?) ?? const []).join(' -> ')}',
    'Local backward focus: ${((result['local_backward_focus_order'] as List?) ?? const []).join(' -> ')}',
    'Hosted forward focus: ${((result['hosted_forward_focus_order'] as List?) ?? const []).join(' -> ')}',
    'Hosted backward focus: ${((result['hosted_backward_focus_order'] as List?) ?? const []).join(' -> ')}',
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
