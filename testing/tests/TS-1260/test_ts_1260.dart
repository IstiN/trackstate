import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../../core/models/workspace_onboarding_contrast_observation.dart';
import '../../fixtures/workspace_onboarding_accessibility_screen_fixture.dart';

const String _ticketKey = 'TS-1260';
const String _ticketSummary =
    'Local onboarding flow field labels — contrast for Repository Path and Branch meets AA requirements';
const String _testFilePath = 'testing/tests/TS-1260/test_ts_1260.dart';
const String _runCommand =
    'flutter test testing/tests/TS-1260/test_ts_1260.dart --reporter expanded';
const String _expectedForegroundHex = '#5B5A52';
const String _expectedBackgroundHex = '#FFFFFF';
const String _expectedRoundedContrast = '6.93';

const List<String> _requestSteps = <String>[
  'Open the application to the first-launch onboarding screen.',
  "Stay on the 'Local folder' setup flow.",
  "Identify the visible labels for 'Repository Path' and 'Branch', and the helper text 'Enter the local Git folder path.'.",
  'Measure the contrast ratio of these text elements against the white (#FFFFFF) background using a contrast analysis tool or widget test.',
];

const List<String> _requiredVisibleTexts = <String>[
  'Repository Path',
  'Branch',
  'Enter the local Git folder path.',
];

const List<String> _requiredLocalFlowTexts = <String>[
  'Add workspace',
  'Local folder',
  'Hosted repository',
  'Open existing folder',
  'Initialize folder',
];

const List<String> _requiredObservationLabels = <String>[
  'Repository Path label',
  'Local path helper',
  'Branch label',
];

void main() {
  testWidgets(
    'TS-1260 local onboarding labels keep AA contrast on the live first-launch screen',
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

        final missingEntryTexts = _missingExpectedTexts(
          expected: _requiredLocalFlowTexts,
          observed: visibleTexts,
        );
        final step1Passed = missingEntryTexts.isEmpty;
        _recordStep(
          result,
          step: 1,
          status: step1Passed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed:
              'missing_visible_texts=${missingEntryTexts.join(', ')}; visible_texts=${visibleTexts.join(' | ')}',
        );
        if (!step1Passed) {
          failures.add(
            'Step 1 failed: the first-launch onboarding screen did not expose the expected initial local onboarding surface.\n'
            'Missing visible texts: ${missingEntryTexts.join(', ')}\n'
            'Observed visible texts: ${visibleTexts.join(' | ')}',
          );
        }

        final step2Passed =
            visibleTexts.contains('Open existing folder') &&
            visibleTexts.contains('Initialize folder') &&
            !visibleTexts.contains('Open');
        result['local_flow_visible'] = step2Passed;
        _recordStep(
          result,
          step: 2,
          status: step2Passed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed:
              'local_actions_present=${visibleTexts.contains('Open existing folder') && visibleTexts.contains('Initialize folder')}; hosted_open_visible=${visibleTexts.contains('Open')}; visible_texts=${visibleTexts.join(' | ')}',
        );
        if (!step2Passed) {
          failures.add(
            "Step 2 failed: onboarding did not remain on the production Local folder setup flow.\n"
            "Expected the local actions 'Open existing folder' and 'Initialize folder' without the hosted 'Open' action.\n"
            'Observed visible texts: ${visibleTexts.join(' | ')}',
          );
        }

        final missingTargetTexts = _missingExpectedTexts(
          expected: _requiredVisibleTexts,
          observed: visibleTexts,
        );
        final step3Passed = missingTargetTexts.isEmpty;
        _recordStep(
          result,
          step: 3,
          status: step3Passed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'missing_target_texts=${missingTargetTexts.join(', ')}; visible_texts=${visibleTexts.join(' | ')}',
        );
        if (!step3Passed) {
          failures.add(
            'Step 3 failed: the required local onboarding labels/helper text were not all visible to the user.\n'
            'Missing texts: ${missingTargetTexts.join(', ')}\n'
            'Observed visible texts: ${visibleTexts.join(' | ')}',
          );
        }

        final contrastObservations = <WorkspaceOnboardingContrastObservation>[];
        final missingObservationLabels = <String>[];
        final contrastFailures = <String>[];
        if (step3Passed) {
          final allObservations = screen.observeContrastSet();
          for (final label in _requiredObservationLabels) {
            final match = _findObservationOrNull(
              observations: allObservations,
              label: label,
            );
            if (match == null) {
              missingObservationLabels.add(label);
              continue;
            }
            contrastObservations.add(match);
            if (!match.passes) {
              contrastFailures.add(
                '${match.label} rendered ${match.contrastRatio.toStringAsFixed(2)}:1, below ${match.minimumContrast.toStringAsFixed(1)}:1.',
              );
            }
            if (match.foregroundHex != _expectedForegroundHex) {
              contrastFailures.add(
                '${match.label} rendered foreground ${match.foregroundHex} instead of $_expectedForegroundHex.',
              );
            }
            if (match.backgroundHex != _expectedBackgroundHex) {
              contrastFailures.add(
                '${match.label} rendered background ${match.backgroundHex} instead of $_expectedBackgroundHex.',
              );
            }
            if (match.contrastRatio.toStringAsFixed(2) !=
                _expectedRoundedContrast) {
              contrastFailures.add(
                '${match.label} rendered ${match.contrastRatio.toStringAsFixed(2)}:1 instead of $_expectedRoundedContrast:1.',
              );
            }
          }
        }
        result['contrast_observations'] = contrastObservations
            .map(_contrastAsMap)
            .toList();
        final step4Passed =
            step3Passed &&
            missingObservationLabels.isEmpty &&
            contrastFailures.isEmpty &&
            contrastObservations.length == _requiredObservationLabels.length;
        _recordStep(
          result,
          step: 4,
          status: step4Passed ? 'passed' : 'failed',
          action: _requestSteps[3],
          observed: step3Passed
              ? 'missing_observation_labels=${missingObservationLabels.join(', ')}; contrast=${contrastObservations.map(_formatObservation).join(' || ')}; contrast_failures=${contrastFailures.join(' || ')}'
              : 'contrast_unavailable=true; missing_target_texts=${missingTargetTexts.join(', ')}',
        );
        if (!step4Passed) {
          failures.add(
            step3Passed
                ? 'Step 4 failed: the ticketed onboarding labels/helper did not all render with the expected AA-compliant live contrast outcome.\n'
                      'Missing contrast observations: ${missingObservationLabels.join(', ')}\n'
                      'Observed contrast: ${contrastObservations.map(_formatObservation).join(' || ')}\n'
                      'Contrast mismatches: ${contrastFailures.join(' || ')}'
                : 'Step 4 failed: contrast could not be measured because one or more required labels/helper texts were not visible on the Local folder flow.',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the first-launch onboarding screen as a user would and confirmed the app opened on the Local folder path rather than the hosted repository path.',
          observed: 'visible_texts=${visibleTexts.join(' | ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Checked the visible copy in place on the local form, specifically the Repository Path label, Branch label, and Enter the local Git folder path. helper text.',
          observed:
              'required_texts_visible=${step3Passed}; missing_target_texts=${missingTargetTexts.join(', ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Inspected the live rendered contrast result a user actually sees on the white onboarding surface for the three ticketed text elements.',
          observed: contrastObservations.isEmpty
              ? 'contrast_unavailable=true'
              : contrastObservations.map(_formatObservation).join(' || '),
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

List<String> _missingExpectedTexts({
  required List<String> expected,
  required List<String> observed,
}) {
  return expected
      .where((text) => !observed.any((candidate) => candidate.contains(text)))
      .toList(growable: false);
}

WorkspaceOnboardingContrastObservation? _findObservationOrNull({
  required List<WorkspaceOnboardingContrastObservation> observations,
  required String label,
}) {
  for (final observation in observations) {
    if (observation.label == label) {
      return observation;
    }
  }
  return null;
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

String _formatObservation(WorkspaceOnboardingContrastObservation observation) {
  return '${observation.label}="${observation.text}" foreground=${observation.foregroundHex} background=${observation.backgroundHex} contrast=${observation.contrastRatio.toStringAsFixed(2)}:1 minimum=${observation.minimumContrast.toStringAsFixed(1)}:1 passes=${observation.passes}';
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
    '* Stayed on the visible {noformat}Local folder{noformat} setup flow and checked that the local actions remained on-screen.',
    '* Verified the visible {noformat}Repository Path{noformat} label, {noformat}Branch{noformat} label, and {noformat}Enter the local Git folder path.{noformat} helper text were present on the user-facing local form.',
    '* Measured the rendered contrast of those three live text elements against the white onboarding surface and checked the deployed muted-token outcome {noformat}#5B5A52{noformat} on {noformat}#FFFFFF{noformat} at {noformat}6.93:1{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: all three ticketed local onboarding text elements were visible on the Local folder flow and rendered at AA-compliant contrast with the deployed muted token outcome.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
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
    '- Opened the production first-launch onboarding screen with no saved workspace profiles.',
    '- Stayed on the visible `Local folder` setup flow and checked that the local actions remained on-screen.',
    '- Verified the visible `Repository Path` label, `Branch` label, and `Enter the local Git folder path.` helper text were present on the user-facing local form.',
    '- Measured the rendered contrast of those three live text elements against the white onboarding surface and checked the deployed muted-token outcome `#5B5A52` on `#FFFFFF` at `6.93:1`.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: all three ticketed local onboarding text elements were visible on the Local folder flow and rendered at AA-compliant contrast with the deployed muted token outcome.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `flutter test` / `${Platform.operatingSystem}`',
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
    '# TS-1260',
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
  final contrastLogs = ((result['contrast_observations'] as List?) ?? const [])
      .whereType<Map>()
      .map(
        (entry) =>
            '${entry['label']}="${entry['text']}" foreground=${entry['foreground_hex']} background=${entry['background_hex']} contrast=${(entry['contrast_ratio'] as num).toStringAsFixed(2)}:1 minimum=${(entry['minimum_contrast'] as num).toStringAsFixed(1)}:1 passes=${entry['passes']}',
      )
      .join(' || ');

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
    'The local onboarding `Repository Path` label, `Branch` label, and `Enter the local Git folder path.` helper text should all be visible on the first-launch `Local folder` flow and render against `#FFFFFF` at at least `4.5:1`, specifically the deployed muted-token outcome `#5B5A52` at `6.93:1`.',
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
    '- Browser/URL: `N/A - Flutter widget test of the first-launch onboarding screen`',
    '- Repository path: `${Directory.current.path}`',
    '',
    '## Actual vs Expected',
    '- Expected: visible local onboarding labels/helper text use `#5B5A52` on `#FFFFFF` at `6.93:1` and satisfy the `4.5:1` AA threshold.',
    '- Actual: ${contrastLogs.isEmpty ? 'contrast could not be recorded because the required visible text was missing or the measurement step failed.' : contrastLogs}',
    '',
    '## Relevant logs',
    '```',
    'Visible texts: ${((result['visible_texts'] as List?) ?? const []).join(' | ')}',
    'Contrast observations: $contrastLogs',
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
    yield '- **Step ${step['step']} — ${('${step['status']}').toUpperCase()}**';
    yield '  - Action: ${step['action']}';
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
  for (final step
      in (result['steps'] as List? ?? const <Object?>[]).whereType<Map>()) {
    if (step['step'] == stepNumber) {
      final status = '${step['status']}'.toUpperCase() == 'PASSED'
          ? '✅ Passed'
          : '❌ Failed';
      return '$status — ${step['observed']}';
    }
  }
  return '❌ Failed — step result was not recorded.';
}
