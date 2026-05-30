import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/ui/core/trackstate_theme.dart';
import 'package:trackstate/ui/features/tracker/views/trackstate_app.dart';

import '../../components/screens/workspace_onboarding_accessibility_robot.dart';
import '../../core/models/workspace_onboarding_contrast_observation.dart';
import '../../core/utils/theme_token_policy_probe.dart';

const String _ticketKey = 'TS-1261';
const String _ticketSummary =
    'SettingsTextField wrapper — labels and helper text use muted theme token';
const String _linkedBug = 'TS-1254';
const String _testFilePath = 'testing/tests/TS-1261/test_ts_1261.dart';
const String _sourceFilePath =
    'lib/ui/features/tracker/views/trackstate_app.dart';
const String _runCommand =
    'flutter test testing/tests/TS-1261/test_ts_1261.dart --reporter expanded';
const Size _viewport = Size(1440, 900);
const String _expectedMutedHex = '#5B5A52';
const String _expectedSurfaceHex = '#FFFFFF';

const List<String> _requestSteps = <String>[
  "Access the source code or widget definition for the 'SettingsTextField' component.",
  "Check the color assignment for the 'label' and 'helperText' style properties.",
  "Confirm that the component is configured to use 'TrackStateColors.light.muted' (#5B5A52).",
];

const List<String> _requiredVisibleTexts = <String>[
  'Repository Path',
  'Enter the local Git folder path.',
  'Branch',
];

const List<String> _requiredObservationLabels = <String>[
  'Repository Path label',
  'Local path helper',
  'Branch label',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-1261 SettingsTextField keeps label and helper text on the muted theme token',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'linked_bug': _linkedBug,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'viewport': '1440x900',
        'run_command': _runCommand,
        'test_file_path': _testFilePath,
        'source_file_path': _sourceFilePath,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final failures = <String>[];

      try {
        tester.view.physicalSize = _viewport;
        tester.view.devicePixelRatio = 1;

        final expectedMutedColor = TrackStateColors.light.muted;
        final expectedSurfaceColor = TrackStateColors.light.surface;
        final expectedMutedHex = _rgbHex(expectedMutedColor);
        final expectedSurfaceHex = _rgbHex(expectedSurfaceColor);
        result['expected_muted_hex'] = expectedMutedHex;
        result['expected_surface_hex'] = expectedSurfaceHex;

        final sourceFile = File('${Directory.current.path}/$_sourceFilePath');
        final sourceExists = sourceFile.existsSync();
        final source = sourceExists ? sourceFile.readAsStringSync() : '';
        final settingsTextFieldBlock = sourceExists
            ? _extractSettingsTextFieldBlock(source)
            : null;
        final classFound = settingsTextFieldBlock != null;
        final labelUsesMuted =
            settingsTextFieldBlock?.contains(
              'return labelBaseStyle.copyWith(color: colors.muted);',
            ) ??
            false;
        final helperUsesMuted =
            settingsTextFieldBlock?.contains(
              'return helperBaseStyle.copyWith(color: colors.muted);',
            ) ??
            false;
        final decorationWiresLabelStyle =
            settingsTextFieldBlock?.contains('labelStyle: labelStyle,') ??
            false;
        final decorationWiresFloatingLabelStyle =
            settingsTextFieldBlock?.contains(
              'floatingLabelStyle: labelStyle,',
            ) ??
            false;
        final decorationWiresHelperStyle =
            settingsTextFieldBlock?.contains('helperStyle: helperStyle,') ??
            false;
        final sourceStepPassed =
            sourceExists &&
            classFound &&
            labelUsesMuted &&
            helperUsesMuted &&
            decorationWiresLabelStyle &&
            decorationWiresFloatingLabelStyle &&
            decorationWiresHelperStyle &&
            expectedMutedHex == _expectedMutedHex &&
            expectedSurfaceHex == _expectedSurfaceHex;
        result['settings_text_field_source_found'] = classFound;
        result['label_uses_muted_token'] = labelUsesMuted;
        result['helper_uses_muted_token'] = helperUsesMuted;
        result['decoration_wires_label_style'] = decorationWiresLabelStyle;
        result['decoration_wires_floating_label_style'] =
            decorationWiresFloatingLabelStyle;
        result['decoration_wires_helper_style'] = decorationWiresHelperStyle;

        _recordStep(
          result,
          step: 1,
          status: sourceStepPassed ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed:
              'source_exists=$sourceExists; settings_text_field_found=$classFound; '
              'label_uses_muted_token=$labelUsesMuted; '
              'helper_uses_muted_token=$helperUsesMuted; '
              'decoration_wires_label_style=$decorationWiresLabelStyle; '
              'decoration_wires_floating_label_style=$decorationWiresFloatingLabelStyle; '
              'decoration_wires_helper_style=$decorationWiresHelperStyle; '
              'expected_muted_hex=$expectedMutedHex; expected_surface_hex=$expectedSurfaceHex',
        );
        if (!sourceStepPassed) {
          failures.add(
            'Step 1 failed: the production SettingsTextField source contract did not keep the shared label/helper styling wired through the muted theme token.\n'
            'Observed: source_exists=$sourceExists; settings_text_field_found=$classFound; '
            'label_uses_muted_token=$labelUsesMuted; helper_uses_muted_token=$helperUsesMuted; '
            'decoration_wires_label_style=$decorationWiresLabelStyle; '
            'decoration_wires_floating_label_style=$decorationWiresFloatingLabelStyle; '
            'decoration_wires_helper_style=$decorationWiresHelperStyle; '
            'expected_muted_hex=$expectedMutedHex; expected_surface_hex=$expectedSurfaceHex',
          );
        }

        await tester.pumpWidget(
          TrackStateApp(
            key: const ValueKey('ts-1261-app'),
            repositoryFactory: () => const DemoTrackStateRepository(),
          ),
        );
        await tester.pumpAndSettle();

        final robot = WorkspaceOnboardingAccessibilityRobot(tester);
        final visibleTexts = robot.visibleTexts();
        result['visible_texts'] = visibleTexts;
        final missingVisibleTexts = _missingExpectedLabels(
          expected: _requiredVisibleTexts,
          observed: visibleTexts,
        );

        List<WorkspaceOnboardingContrastObservation> fieldObservations =
            const <WorkspaceOnboardingContrastObservation>[];
        String? observationError;
        if (missingVisibleTexts.isEmpty) {
          try {
            fieldObservations = robot
                .observeContrastSet()
                .where(
                  (observation) =>
                      _requiredObservationLabels.contains(observation.label),
                )
                .toList(growable: false);
          } on StateError catch (error) {
            observationError = error.toString();
          }
        }

        result['field_observations'] = fieldObservations
            .map(_observationAsMap)
            .toList();
        result['observation_error'] = observationError;

        final missingObservationLabels = _requiredObservationLabels
            .where(
              (label) => !fieldObservations.any(
                (observation) => observation.label == label,
              ),
            )
            .toList(growable: false);
        final wrongForeground = fieldObservations
            .where(
              (observation) => observation.foregroundHex != expectedMutedHex,
            )
            .toList(growable: false);
        final wrongBackground = fieldObservations
            .where(
              (observation) => observation.backgroundHex != expectedSurfaceHex,
            )
            .toList(growable: false);
        final failingContrast = fieldObservations
            .where((observation) => !observation.passes)
            .toList(growable: false);
        final liveRenderingStepPassed =
            missingVisibleTexts.isEmpty &&
            observationError == null &&
            missingObservationLabels.isEmpty &&
            wrongForeground.isEmpty &&
            wrongBackground.isEmpty &&
            failingContrast.isEmpty;

        _recordStep(
          result,
          step: 2,
          status: liveRenderingStepPassed ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed:
              'visible_texts=${visibleTexts.join(' | ')}; '
              'missing_visible_texts=${missingVisibleTexts.join(', ')}; '
              'field_observations=${_formatObservations(fieldObservations)}; '
              'missing_observation_labels=${missingObservationLabels.join(', ')}; '
              'wrong_foreground=${_formatObservations(wrongForeground)}; '
              'wrong_background=${_formatObservations(wrongBackground)}; '
              'failing_contrast=${_formatObservations(failingContrast)}; '
              'observation_error=${observationError ?? '<none>'}',
        );
        if (!liveRenderingStepPassed) {
          failures.add(
            'Step 2 failed: the production onboarding screen did not render the SettingsTextField label/helper text surfaces with the expected muted token styling.\n'
            'Missing visible texts: ${missingVisibleTexts.join(', ')}\n'
            'Missing observation labels: ${missingObservationLabels.join(', ')}\n'
            'Wrong foreground observations: ${_formatObservations(wrongForeground)}\n'
            'Wrong background observations: ${_formatObservations(wrongBackground)}\n'
            'Failing contrast observations: ${_formatObservations(failingContrast)}\n'
            'Observation error: ${observationError ?? '<none>'}\n'
            'Observed visible texts: ${visibleTexts.join(' | ')}\n'
            'Observed field observations: ${_formatObservations(fieldObservations)}',
          );
        }

        final tokenCheck =
            await tester.runAsync(_runThemeTokenCheck) ??
            <String, Object?>{
              'command': 'dart tool/check_theme_tokens.dart $_sourceFilePath',
              'exit_code': 1,
              'output': 'Theme token policy probe did not return a result.',
            };
        result['theme_token_check'] = tokenCheck;
        final themeTokenStepPassed =
            tokenCheck['exit_code'] == 0 &&
            !'${tokenCheck['output'] ?? ''}'.contains('warning •');

        _recordStep(
          result,
          step: 3,
          status: themeTokenStepPassed ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed:
              'command=${tokenCheck['command']}; '
              'exit_code=${tokenCheck['exit_code']}; '
              'output=${_singleLine(tokenCheck['output'])}',
        );
        if (!themeTokenStepPassed) {
          failures.add(
            'Step 3 failed: the repository theme-token policy command did not confirm the SettingsTextField implementation stayed on the shared muted token.\n'
            'Command: ${tokenCheck['command']}\n'
            'Exit code: ${tokenCheck['exit_code']}\n'
            'Output:\n${tokenCheck['output']}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Viewed the first-launch onboarding screen exactly as a user would see it before any workspace is saved and checked that the Repository Path label, helper text, and Branch label were visible in the disabled field hints.',
          observed:
              'visible_texts=${visibleTexts.join(' | ')}; missing_visible_texts=${missingVisibleTexts.join(', ')}',
        );
        _recordHumanVerification(
          result,
          check:
              'Inspected the rendered field label/helper text surfaces from the user-visible onboarding screen and confirmed they matched the muted token on the white input surface.',
          observed:
              'expected_muted_hex=$expectedMutedHex; expected_surface_hex=$expectedSurfaceHex; field_observations=${_formatObservations(fieldObservations)}',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        _writeFailureOutputs(
          result,
          writeBugDescription: error is AssertionError,
        );
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
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
  return runThemeTokenPolicyCheck(<String>[_sourceFilePath]);
}

String? _extractSettingsTextFieldBlock(String source) {
  const startMarker = 'class _SettingsTextField extends StatelessWidget {';
  const endMarker = 'class _SurfaceCard extends StatelessWidget {';
  final start = source.indexOf(startMarker);
  if (start == -1) {
    return null;
  }
  final end = source.indexOf(endMarker, start);
  if (end == -1) {
    return source.substring(start);
  }
  return source.substring(start, end);
}

List<String> _missingExpectedLabels({
  required List<String> expected,
  required List<String> observed,
}) {
  return expected
      .where((label) => !observed.any((candidate) => candidate.contains(label)))
      .toList(growable: false);
}

Map<String, Object?> _observationAsMap(
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

String _formatObservations(
  List<WorkspaceOnboardingContrastObservation> observations,
) {
  if (observations.isEmpty) {
    return '<none>';
  }
  return observations
      .map(
        (observation) =>
            '${observation.label}: text="${observation.text}", foreground=${observation.foregroundHex}, '
            'background=${observation.backgroundHex}, contrast=${observation.contrastRatio.toStringAsFixed(2)}, '
            'minimum=${observation.minimumContrast.toStringAsFixed(2)}, passes=${observation.passes}',
      )
      .join(' || ');
}

String _rgbHex(Color color) {
  final rgb = color.toARGB32() & 0x00FFFFFF;
  return '#${rgb.toRadixString(16).padLeft(6, '0').toUpperCase()}';
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
    '*Linked Bug:* $_linkedBug',
    '',
    'h4. What was tested',
    '* Opened the production first-launch onboarding screen in a Flutter widget test at {noformat}${result['viewport']}{noformat} with empty shared preferences.',
    '* Inspected the private {noformat}_SettingsTextField{noformat} implementation in {noformat}$_sourceFilePath{noformat} to verify the default label/helper style wiring stays on {noformat}colors.muted{noformat}.',
    '* Verified the user-visible {noformat}Repository Path{noformat} label, {noformat}Enter the local Git folder path.{noformat} helper text, and {noformat}Branch{noformat} label render with the muted light-theme token on the white field surface.',
    '* Ran the repository theme-token policy command against {noformat}$_sourceFilePath{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: {noformat}_SettingsTextField{noformat} kept its default label/helper styling on the muted token, and the visible onboarding field labels/helper text rendered as {noformat}${result['expected_muted_hex']}{noformat} on {noformat}${result['expected_surface_hex']}{noformat}.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}${result['environment']} / ${result['os']}{noformat}',
    '* Viewport: {noformat}${result['viewport']}{noformat}',
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
    '**Test Case:** $_ticketKey - $_ticketSummary  ',
    '**Linked Bug:** $_linkedBug',
    '',
    '### What was tested',
    '- Opened the production first-launch onboarding screen in a Flutter widget test at `${result['viewport']}` with empty shared preferences.',
    '- Inspected the private `_SettingsTextField` implementation in `$_sourceFilePath` to verify the default label/helper style wiring stays on `colors.muted`.',
    '- Verified the user-visible `Repository Path` label, `Enter the local Git folder path.` helper text, and `Branch` label render with the muted light-theme token on the white field surface.',
    '- Ran the repository theme-token policy command against `$_sourceFilePath`.',
    '',
    '### Result',
    passed
        ? '- Matched the expected result: `_SettingsTextField` kept its default label/helper styling on the muted token, and the visible onboarding field labels/helper text rendered as `${result['expected_muted_hex']}` on `${result['expected_surface_hex']}`.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '- Environment: `${result['environment']}` / `${result['os']}`',
    '- Viewport: `${result['viewport']}`',
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
    '# $_ticketKey',
    '',
    '- Status: $statusLabel',
    '- Test case: $_ticketSummary',
    '- Linked bug: $_linkedBug',
    '- Run command: `$_runCommand`',
    '- Environment: `${result['environment']}` on `${result['os']}`',
    '- Viewport: `${result['viewport']}`',
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
    'The production `_SettingsTextField` wrapper should keep default `labelStyle`, `floatingLabelStyle`, and `helperStyle` on the shared muted theme token so the first-launch onboarding `Repository Path` label, `Enter the local Git folder path.` helper text, and `Branch` label all render with `TrackStateColors.light.muted` (`$_expectedMutedHex`) on the white field surface (`$_expectedSurfaceHex`).',
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
    '## Actual vs expected',
    '- Expected muted token: `${result['expected_muted_hex'] ?? _expectedMutedHex}` on `${result['expected_surface_hex'] ?? _expectedSurfaceHex}` for the visible onboarding label/helper text surfaces.',
    '- Actual visible texts: `${((result['visible_texts'] as List?) ?? const []).join(' | ')}`',
    '- Actual field observations: `${_fieldObservationLog(result)}`',
    '',
    '## Environment',
    '- Command: `$_runCommand`',
    '- OS: `${result['os']}`',
    '- Runtime: `${result['environment']}`',
    '- Viewport: `${result['viewport']}`',
    '- Repository path: `${Directory.current.path}`',
    '- Source file: `$_sourceFilePath`',
    '',
    '## Relevant logs',
    '```',
    'Visible texts: ${((result['visible_texts'] as List?) ?? const []).join(' | ')}',
    'Field observations: ${_fieldObservationLog(result)}',
    'Source contract: settings_text_field_found=${result['settings_text_field_source_found']}; label_uses_muted_token=${result['label_uses_muted_token']}; helper_uses_muted_token=${result['helper_uses_muted_token']}; decoration_wires_label_style=${result['decoration_wires_label_style']}; decoration_wires_floating_label_style=${result['decoration_wires_floating_label_style']}; decoration_wires_helper_style=${result['decoration_wires_helper_style']}',
    'Theme token policy output: ${_singleLine((result['theme_token_check'] as Map?)?['output'])}',
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
    yield '- **Check**: ${item['check']}';
    yield '  - Observed: `${item['observed']}`';
  }
}

String _stepOutcome(Map<String, Object?> result, int stepNumber) {
  final step = (result['steps'] as List? ?? const <Object?>[])
      .whereType<Map>()
      .firstWhere(
        (candidate) => candidate['step'] == stepNumber,
        orElse: () => const <String, Object?>{},
      );
  if (step.isEmpty) {
    return 'Not executed.';
  }
  final status = '${step['status']}'.toUpperCase();
  return '$status — ${step['observed']}';
}

String _fieldObservationLog(Map<String, Object?> result) {
  final entries = (result['field_observations'] as List? ?? const <Object?>[])
      .whereType<Map>()
      .map(
        (entry) =>
            '${entry['label']}: text="${entry['text']}", foreground=${entry['foreground_hex']}, '
            'background=${entry['background_hex']}, contrast=${entry['contrast_ratio']}, minimum=${entry['minimum_contrast']}, passes=${entry['passes']}',
      )
      .toList(growable: false);
  if (entries.isEmpty) {
    return '<none>';
  }
  return entries.join(' || ');
}

String _singleLine(Object? value) {
  return '${value ?? ''}'.replaceAll('\n', r'\n');
}
