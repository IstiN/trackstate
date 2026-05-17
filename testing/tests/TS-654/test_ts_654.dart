import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';

import '../../core/fakes/reactive_issue_detail_trackstate_repository.dart';
import '../../core/interfaces/issue_detail_accessibility_screen.dart';
import '../../fixtures/issue_detail_accessibility_screen_fixture.dart';

const String _ticketKey = 'TS-654';
const String _environment = 'flutter widget test';
const String _issueKey = 'TRACK-12';
const String _issueSummary = 'Implement Git sync service';
const String _targetIssueKey = 'TRACK-11';
const String _linksPath = 'TRACK-12/links.json';
const String _invalidLinksJson = '''
[
  {
    "type": "blocks",
    "target": "TRACK-11",
    "direction": "inward"
  }
]
''';
const List<String> _expectedWarningFragments = <String>[
  'warning',
  'blocks',
  'inward',
  'outward',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-654 logs a validation warning when issue detail opens with non-canonical link metadata',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'environment': _environment,
        'os': Platform.operatingSystem,
        'issue_key': _issueKey,
        'issue_summary': _issueSummary,
        'links_path': _linksPath,
        'seeded_payload': _invalidLinksJson.trim(),
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final repository = ReactiveIssueDetailTrackStateRepository(
        textFixtures: const <String, String>{_linksPath: _invalidLinksJson},
      );
      final logCapture = _UiWarningLogCapture()..install();
      IssueDetailAccessibilityScreenHandle? screen;

      try {
        final seededIssue = await _hydrateIssue(repository);
        result['hydrated_links'] = _formatIssueLinks(seededIssue.links);
        if (!_containsInvalidLink(seededIssue.links)) {
          throw AssertionError(
            'Precondition failed: $_linksPath did not hydrate into the expected non-canonical '
            '`blocks` + `inward` relationship for $_issueKey.\n'
            'Observed hydrated links: ${_formatIssueLinks(seededIssue.links)}',
          );
        }

        await logCapture.capture(() async {
          screen = await launchIssueDetailAccessibilityFixture(
            tester,
            repository: repository,
          );
          await screen!.openSearch();
          await screen!.selectIssue(_issueKey, _issueSummary);
          await tester.pump(const Duration(milliseconds: 300));
          await tester.pumpAndSettle();
        });

        final issueTexts = screen!.visibleTextsWithinIssueDetail(_issueKey);
        final issueSemantics = screen!.semanticsLabelsInIssueDetail(_issueKey);
        final issueButtons = screen!.buttonLabelsInIssueDetail(_issueKey);
        final frameworkExceptions = _drainFrameworkExceptions(tester);
        final capturedLogs = logCapture.messages;
        final normalizedLogs = capturedLogs.join('\n').toLowerCase();
        final missingWarningFragments = _expectedWarningFragments
            .where((fragment) => !normalizedLogs.contains(fragment))
            .toList(growable: false);

        result['issue_visible_texts'] = issueTexts;
        result['issue_semantics'] = issueSemantics;
        result['issue_button_labels'] = issueButtons;
        result['captured_logs'] = capturedLogs;
        result['framework_exceptions'] = frameworkExceptions;

        if (!screen!.showsIssueDetail(_issueKey)) {
          throw AssertionError(
            'Step 1 failed: navigating to $_issueKey did not render the issue detail surface.\n'
            'Visible texts: ${_formatSnapshot(issueTexts)}\n'
            'Visible semantics: ${_formatSnapshot(issueSemantics)}\n'
            'Captured logs:\n${_formatLogBlock(capturedLogs)}',
          );
        }
        if (!_containsSnapshot(issueTexts, _issueSummary) &&
            !_containsSnapshot(issueSemantics, _issueSummary)) {
          throw AssertionError(
            'Step 1 failed: the issue detail surface did not expose the expected user-facing '
            'summary "$_issueSummary".\n'
            'Visible texts: ${_formatSnapshot(issueTexts)}\n'
            'Visible semantics: ${_formatSnapshot(issueSemantics)}',
          );
        }
        _recordStep(
          result,
          step: 1,
          status: 'passed',
          action:
              'Navigate to the issue detail view in the TrackState web interface.',
          observed:
              'issue=$_issueKey; summary=$_issueSummary; visible_texts=${_formatSnapshot(issueTexts)}; '
              'visible_semantics=${_formatSnapshot(issueSemantics)}; visible_buttons=${_formatSnapshot(issueButtons)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Verified as a user that opening $_issueKey showed the issue detail surface with the expected summary instead of leaving the view blank, crashing, or staying on search results.',
          observed:
              'visible_texts=${_formatSnapshot(issueTexts)}; visible_semantics=${_formatSnapshot(issueSemantics)}',
        );

        final step2Observation =
            'missing_warning_fragments=${missingWarningFragments.isEmpty ? "<none>" : missingWarningFragments.join(", ")}; '
            'captured_logs=${_formatSnapshot(capturedLogs)}; '
            'framework_exceptions=${_formatSnapshot(frameworkExceptions)}';
        _recordHumanVerification(
          result,
          check:
              'Reviewed the captured system logs produced while opening the issue detail view to confirm the warning a user or maintainer would inspect mentions the non-canonical `blocks` / `inward` metadata and the expected `outward` direction.',
          observed: _formatLogBlock(capturedLogs),
        );
        if (missingWarningFragments.isNotEmpty) {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action:
                'Inspect the browser console or system logs for schema validation warnings.',
            observed: step2Observation,
          );
          throw AssertionError(
            'Step 2 failed: opening $_issueKey with non-canonical link metadata did not emit '
            'the expected schema validation warning in captured system logs.\n'
            'Missing log fragments: ${missingWarningFragments.join(', ')}\n'
            'Captured logs:\n${_formatLogBlock(capturedLogs)}\n'
            'Framework exceptions:\n${_formatLogBlock(frameworkExceptions)}\n'
            'Hydrated issue links: ${_formatIssueLinks(seededIssue.links)}\n'
            'Visible issue detail texts: ${_formatSnapshot(issueTexts)}\n'
            'Visible issue detail semantics: ${_formatSnapshot(issueSemantics)}',
          );
        }
        _recordStep(
          result,
          step: 2,
          status: 'passed',
          action:
              'Inspect the browser console or system logs for schema validation warnings.',
          observed: step2Observation,
        );

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        result['captured_logs'] ??= logCapture.messages;
        if (screen != null) {
          result['issue_visible_texts'] ??= screen!
              .visibleTextsWithinIssueDetail(_issueKey);
          result['issue_semantics'] ??= screen!.semanticsLabelsInIssueDetail(
            _issueKey,
          );
          result['issue_button_labels'] ??= screen!.buttonLabelsInIssueDetail(
            _issueKey,
          );
        }
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        logCapture.dispose();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

Future<TrackStateIssue> _hydrateIssue(
  ReactiveIssueDetailTrackStateRepository repository,
) async {
  final searchResults = await repository.searchIssues(_issueKey);
  final issue = searchResults.firstWhere(
    (candidate) => candidate.key == _issueKey,
    orElse: () => throw AssertionError(
      'Precondition failed: the seeded repository did not expose $_issueKey in search results.',
    ),
  );
  return repository.hydrateIssue(issue);
}

bool _containsInvalidLink(List<IssueLink> links) {
  return links.any(
    (link) =>
        link.type == 'blocks' &&
        link.targetKey == _targetIssueKey &&
        link.direction == 'inward',
  );
}

List<String> _drainFrameworkExceptions(WidgetTester tester) {
  final exceptions = <String>[];
  Object? exception;
  while ((exception = tester.takeException()) != null) {
    exceptions.add(exception.toString());
  }
  return exceptions;
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
  final status = passed ? 'PASSED' : 'FAILED';
  final lines = <String>[
    'h3. $_ticketKey $status',
    '',
    '*Automation coverage*',
    '* Pumped the production TrackState issue-detail UI with $_linksPath seeded as {code:json}${jsonEncode(const <String, String>{'type': 'blocks', 'target': _targetIssueKey, 'direction': 'inward'})}{code}.',
    '* Opened $_issueKey through the JQL Search flow and captured visible issue-detail text, semantics, button labels, and system log output.',
    '* Checked the captured logs for the schema validation warning fragments {{warning}}, {{blocks}}, {{inward}}, and {{outward}}.',
    '',
    '*Observed result*',
    passed
        ? '* Matched the expected result: the issue detail stayed visible and the captured system logs contained the expected schema validation warning.'
        : '* Did not match the expected result.',
    '* Environment: {noformat}$_environment / ${Platform.operatingSystem}{noformat}.',
    '',
    '*Step results*',
    ..._stepLines(result, jira: true),
    '',
    '*Human-style verification*',
    ..._humanLines(result, jira: true),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '*Exact error*',
      '{code}',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '{code}',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _prBody(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'Passed' : 'Failed';
  final lines = <String>[
    '## $_ticketKey $status',
    '',
    '### Automation',
    '- Pumped the production TrackState issue-detail UI with `$_linksPath` seeded as `{"type":"blocks","target":"$_targetIssueKey","direction":"inward"}`.',
    '- Opened `$_issueKey` through the JQL Search flow and captured visible issue-detail text, semantics, button labels, and system log output.',
    '- Checked the captured logs for the schema validation warning fragments `warning`, `blocks`, `inward`, and `outward`.',
    '',
    '### Observed result',
    passed
        ? '- Matched the expected result: the issue detail stayed visible and the captured system logs contained the expected schema validation warning.'
        : '- Did not match the expected result.',
    '- Environment: `$_environment` on `${Platform.operatingSystem}`.',
    '',
    '### Step results',
    ..._stepLines(result, jira: false),
    '',
    '### Human-style verification',
    ..._humanLines(result, jira: false),
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '### Exact error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final status = passed ? 'passed' : 'failed';
  final lines = <String>[
    '# $_ticketKey $status',
    '',
    'Ran a production UI issue-detail scenario with non-canonical link metadata seeded in `$_linksPath`.',
    '',
    '## Observed',
    '- Environment: `$_environment` on `${Platform.operatingSystem}`',
    '- Hydrated links: `${result['hydrated_links'] ?? '<unknown>'}`',
    '- Issue detail texts: `${_formatSnapshot(_stringList(result['issue_visible_texts']))}`',
    '- Captured logs: `${_formatSnapshot(_stringList(result['captured_logs']))}`',
  ];
  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Error',
      '```text',
      '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
      '```',
    ]);
  }
  return '${lines.join('\n')}\n';
}

String _bugDescription(Map<String, Object?> result) {
  return [
    '# TS-654 - Issue detail does not log a validation warning for non-canonical link metadata',
    '',
    '## Steps to reproduce',
    '1. Navigate to the issue detail view in the TrackState web interface.',
    '   - ${_statusEmoji(_stepStatus(result, 1))} ${_stepObservation(result, 1)}',
    '2. Inspect the browser console or system logs for schema validation warnings.',
    '   - ${_statusEmoji(_stepStatus(result, 2))} ${_stepObservation(result, 2)}',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? ''}\n${result['traceback'] ?? ''}',
    '```',
    '',
    '## Actual vs Expected',
    '- **Expected:** opening issue detail for `$_issueKey` with `$_linksPath` containing `{"type":"blocks","target":"$_targetIssueKey","direction":"inward"}` should keep the UI visible and log a schema validation warning that mentions the non-canonical `blocks` / `inward` metadata and the expected `outward` direction.',
    '- **Actual:** ${result['error'] ?? 'the issue detail scenario did not produce the expected warning.'}',
    '',
    '## Environment details',
    '- Runtime: `$_environment`',
    '- OS: `${Platform.operatingSystem}`',
    '- URL: `N/A (widget test pumped TrackStateApp in-memory issue detail flow)`',
    '- Browser: `N/A (widget test system-log capture)`',
    '- Issue: `$_issueKey` (`$_issueSummary`)',
    '- Seeded links path: `$_linksPath`',
    '- Seeded payload: `$_invalidLinksJson`',
    '',
    '## Screenshots or logs',
    '- Screenshot: `N/A (widget test)`',
    '### Captured system logs',
    '```text',
    _formatLogBlock(_stringList(result['captured_logs'])),
    '```',
    '### Visible issue detail text',
    '```text',
    _formatSnapshot(_stringList(result['issue_visible_texts'])),
    '```',
    '### Visible issue detail semantics',
    '```text',
    _formatSnapshot(_stringList(result['issue_semantics'])),
    '```',
    '### Visible issue detail buttons',
    '```text',
    _formatSnapshot(_stringList(result['issue_button_labels'])),
    '```',
  ].join('\n');
}

List<String> _stepLines(Map<String, Object?> result, {required bool jira}) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  return steps.map((Object? rawStep) {
    final step = rawStep as Map<Object?, Object?>;
    final prefix = jira ? '#' : '-';
    return '$prefix Step ${step['step']} (${step['status']}): ${step['action']} Observed: ${step['observed']}';
  }).toList();
}

List<String> _humanLines(Map<String, Object?> result, {required bool jira}) {
  final checks =
      (result['human_verification'] as List<Object?>?) ?? const <Object?>[];
  return checks.map((Object? rawCheck) {
    final check = rawCheck as Map<Object?, Object?>;
    final prefix = jira ? '#' : '-';
    return '$prefix ${check['check']} Observed: ${check['observed']}';
  }).toList();
}

String _stepStatus(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['status'] ?? 'failed'}';
    }
  }
  return 'failed';
}

String _stepObservation(Map<String, Object?> result, int stepNumber) {
  final steps = (result['steps'] as List<Object?>?) ?? const <Object?>[];
  for (final rawStep in steps) {
    final step = rawStep as Map<Object?, Object?>;
    if (step['step'] == stepNumber) {
      return '${step['observed'] ?? '<no observation recorded>'}';
    }
  }
  return '<no observation recorded>';
}

String _statusEmoji(String status) {
  return switch (status) {
    'passed' => '✅',
    'failed' => '❌',
    _ => '⚪',
  };
}

List<String> _stringList(Object? value) {
  if (value is List<String>) {
    return value;
  }
  if (value is List) {
    return value.map((entry) => '$entry').toList(growable: false);
  }
  return const <String>[];
}

String _formatSnapshot(List<String> values) {
  if (values.isEmpty) {
    return '<none>';
  }
  return values.join(' | ');
}

String _formatLogBlock(List<String> lines) {
  if (lines.isEmpty) {
    return '<empty>';
  }
  return lines.join('\n');
}

bool _containsSnapshot(List<String> values, String expected) {
  return values.any((value) => value.contains(expected));
}

String _formatIssueLinks(List<IssueLink> links) {
  if (links.isEmpty) {
    return '<none>';
  }
  return links
      .map((link) => '${link.type}:${link.direction}:${link.targetKey}')
      .join(', ');
}

class _UiWarningLogCapture {
  final List<String> _messages = <String>[];
  DebugPrintCallback? _previousDebugPrint;
  FlutterExceptionHandler? _previousFlutterError;

  List<String> get messages => List<String>.unmodifiable(_messages);

  void install() {
    _previousDebugPrint = debugPrint;
    debugPrint = (String? message, {int? wrapWidth}) {
      if (message != null && message.trim().isNotEmpty) {
        _messages.add(message);
      }
      _previousDebugPrint?.call(message, wrapWidth: wrapWidth);
    };

    _previousFlutterError = FlutterError.onError;
    FlutterError.onError = (FlutterErrorDetails details) {
      _messages.add(_describeFlutterError(details));
      _previousFlutterError?.call(details);
    };
  }

  Future<T> capture<T>(Future<T> Function() action) async {
    Object? zoneError;
    StackTrace? zoneStackTrace;
    T? result;

    await runZonedGuarded(
      () async {
        result = await action();
      },
      (Object error, StackTrace stackTrace) {
        zoneError = error;
        zoneStackTrace = stackTrace;
      },
      zoneSpecification: ZoneSpecification(
        print: (self, parent, zone, line) {
          if (line.trim().isNotEmpty) {
            _messages.add(line);
          }
          parent.print(zone, line);
        },
      ),
    );

    if (zoneError != null) {
      Error.throwWithStackTrace(zoneError!, zoneStackTrace!);
    }

    return result as T;
  }

  void dispose() {
    if (_previousDebugPrint != null) {
      debugPrint = _previousDebugPrint!;
    }
    FlutterError.onError = _previousFlutterError;
  }

  String _describeFlutterError(FlutterErrorDetails details) {
    final buffer = StringBuffer(details.exceptionAsString());

    final library = details.library?.trim();
    if (library != null && library.isNotEmpty) {
      buffer.write('\nLibrary: $library');
    }

    final context = details.context?.toDescription();
    if (context != null && context.isNotEmpty) {
      buffer.write('\nContext: $context');
    }

    final stackTrace = details.stack?.toString().trim();
    if (stackTrace != null && stackTrace.isNotEmpty) {
      buffer.write('\nStack trace:\n$stackTrace');
    }

    return buffer.toString();
  }
}
