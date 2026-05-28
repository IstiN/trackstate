import 'dart:convert';
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../components/factories/testing_dependencies.dart';
import '../../core/interfaces/trackstate_app_component.dart';
import '../TS-741/support/ts741_invalid_domain_scope_repository.dart';

const String _ticketKey = 'TS-755';
const String _ticketSummary =
    'Sync event with unknown domain — issue-level hydration and UI state preserved';
const String _testFilePath = 'testing/tests/TS-755/test_ts_755.dart';
const String _runCommand =
    'flutter test testing/tests/TS-755/test_ts_755.dart --reporter expanded';
const List<String> _requestSteps = <String>[
  "Simulate a background sync event for TRACK-741C using an unknown domain scope (e.g., 'TRACK-741C/sync-domains/unknown-domain.md').",
  'Monitor the hydration calls for the specific issue TRACK-741C (inspect hydration_delta_count).',
  'Observe the visible content in the Comments tab.',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-755 filters unknown hosted sync scopes without issue hydration',
    (tester) async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final semantics = tester.ensureSemantics();
      final TrackStateAppComponent screen = defaultTestingDependencies
          .createTrackStateAppScreen(tester);
      final repository = Ts741InvalidDomainScopeRepository();

      try {
        await repository.connectForTest();
        await screen.pump(repository);

        result['repository'] = 'trackstate/trackstate';
        result['issue_key'] = Ts741InvalidDomainScopeRepository.issueCKey;
        result['unknown_changed_path'] =
            Ts741InvalidDomainScopeRepository.unknownChangedPath;
        result['expected_visible_comment'] =
            Ts741InvalidDomainScopeRepository.initialComment;
        result['unexpected_visible_comment'] =
            Ts741InvalidDomainScopeRepository.hiddenUpdatedComment;

        await screen.openSection('Board');
        await screen.openIssue(
          Ts741InvalidDomainScopeRepository.issueCKey,
          Ts741InvalidDomainScopeRepository.issueCSummary,
        );
        await screen.expectIssueDetailVisible(
          Ts741InvalidDomainScopeRepository.issueCKey,
        );
        final commentsTabOpened = await screen.tapVisibleControl('Comments');
        final initialCommentVisible =
            commentsTabOpened &&
            await screen.isTextVisible(
              Ts741InvalidDomainScopeRepository.initialComment,
            );
        final issueDetailVisible = await screen.isIssueDetailVisible(
          Ts741InvalidDomainScopeRepository.issueCKey,
        );
        final preconditionObserved =
            'comments_tab_opened=$commentsTabOpened; '
            'initial_comment_visible=$initialCommentVisible; '
            'issue_detail_visible=$issueDetailVisible';
        result['precondition'] = preconditionObserved;
        if (!commentsTabOpened ||
            !initialCommentVisible ||
            !issueDetailVisible) {
          throw AssertionError(
            'Precondition failed: the production app did not reach TRACK-741C with the visible Comments tab loaded before the unknown sync scope was simulated.\n'
            'Observed: $preconditionObserved\n'
            'Visible texts: ${_formatSnapshot(screen.visibleTextsSnapshot())}\n'
            'Visible semantics: ${_formatSnapshot(screen.visibleSemanticsLabelsSnapshot())}',
          );
        }

        final baselineHydrationCount = repository.hydrateCalls.length;
        final baselineSyncCheckCount = repository.syncCheckCount;
        final initialRepositoryRevision = repository.repositoryRevision;

        await repository.emitUnknownDomainRefresh();
        await _resumeApp(tester);

        final hydrationDelta = repository.hydrateCalls
            .skip(baselineHydrationCount)
            .toList(growable: false);
        final issueHydrationDelta = hydrationDelta
            .where(
              (call) =>
                  call.issueKey == Ts741InvalidDomainScopeRepository.issueCKey,
            )
            .toList(growable: false);
        final hydrationScopesForIssue = <String>{
          for (final call in issueHydrationDelta) ..._scopeNames(call.scopes),
        }.toList(growable: false)..sort();
        final syncCheckDelta =
            repository.syncCheckCount - baselineSyncCheckCount;
        final initialCommentStillVisible = await screen.isTextVisible(
          Ts741InvalidDomainScopeRepository.initialComment,
        );
        final hiddenUpdatedCommentVisible = await screen.isTextVisible(
          Ts741InvalidDomainScopeRepository.hiddenUpdatedComment,
        );
        final issueDetailStillVisible = await screen.isIssueDetailVisible(
          Ts741InvalidDomainScopeRepository.issueCKey,
        );
        final visibleTextsAfterSync = screen.visibleTextsSnapshot();
        final visibleSemanticsAfterSync = screen
            .visibleSemanticsLabelsSnapshot();

        result['repository_revision_before_sync'] = initialRepositoryRevision;
        result['repository_revision_after_sync'] =
            repository.repositoryRevision;
        result['sync_check_delta'] = syncCheckDelta;
        result['hydration_delta_count'] = issueHydrationDelta.length;
        result['hydration_delta'] = [
          for (final call in issueHydrationDelta)
            <String, Object?>{
              'issue_key': call.issueKey,
              'scopes': _scopeNames(call.scopes),
              'force': call.force,
            },
        ];
        result['hydration_scopes_for_issue'] = hydrationScopesForIssue;
        result['initial_comment_still_visible'] = initialCommentStillVisible;
        result['hidden_updated_comment_visible'] = hiddenUpdatedCommentVisible;
        result['issue_detail_still_visible'] = issueDetailStillVisible;
        result['repository_comment_after_sync'] =
            repository.currentIssueCComment;
        result['visible_texts_after_sync'] = visibleTextsAfterSync;
        result['visible_semantics_after_sync'] = visibleSemanticsAfterSync;

        final failures = <String>[];

        final stepOneObserved =
            'sync_check_delta=$syncCheckDelta; '
            'repository_revision_before=$initialRepositoryRevision; '
            'repository_revision_after=${repository.repositoryRevision}; '
            'changed_path=${Ts741InvalidDomainScopeRepository.unknownChangedPath}';
        _recordStep(
          result,
          step: 1,
          status: syncCheckDelta >= 1 ? 'passed' : 'failed',
          action: _requestSteps[0],
          observed: stepOneObserved,
        );
        if (syncCheckDelta < 1) {
          failures.add(
            'Step 1 failed: the app-resume background sync did not process the unknown hosted change path.\n'
            'Observed: $stepOneObserved',
          );
        }

        final noIssueHydrationDispatched = issueHydrationDelta.isEmpty;
        final stepTwoObserved =
            'hydration_delta_count=${issueHydrationDelta.length}; '
            'hydration_scopes_for_issue=${hydrationScopesForIssue.isEmpty ? '<none>' : hydrationScopesForIssue.join(', ')}; '
            'hydrations=${_formatHydrationCalls(issueHydrationDelta)}';
        _recordStep(
          result,
          step: 2,
          status: noIssueHydrationDispatched ? 'passed' : 'failed',
          action: _requestSteps[1],
          observed: stepTwoObserved,
        );
        if (!noIssueHydrationDispatched) {
          failures.add(
            'Step 2 failed: the unknown sync scope still dispatched hydration for TRACK-741C instead of leaving hydration_delta_count at 0.\n'
            'Observed: $stepTwoObserved',
          );
        }

        final uiStatePreserved =
            initialCommentStillVisible &&
            !hiddenUpdatedCommentVisible &&
            issueDetailStillVisible;
        final stepThreeObserved =
            'initial_comment_still_visible=$initialCommentStillVisible; '
            'hidden_updated_comment_visible=$hiddenUpdatedCommentVisible; '
            'issue_detail_still_visible=$issueDetailStillVisible; '
            'repository_comment_after_sync=${repository.currentIssueCComment}; '
            'visible_texts=${_formatSnapshot(visibleTextsAfterSync)}';
        _recordStep(
          result,
          step: 3,
          status: uiStatePreserved ? 'passed' : 'failed',
          action: _requestSteps[2],
          observed: stepThreeObserved,
        );
        if (!uiStatePreserved) {
          failures.add(
            'Step 3 failed: the visible TRACK-741C Comments tab did not preserve the original user-facing comment after the unknown sync scope.\n'
            'Observed: $stepThreeObserved\n'
            'Visible semantics: ${_formatSnapshot(visibleSemanticsAfterSync)}',
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Kept the real TRACK-741C Comments tab open after the malformed sync event and checked the exact visible comment text where a user would read it.',
          observed:
              'initial_comment_still_visible=$initialCommentStillVisible; hidden_updated_comment_visible=$hiddenUpdatedCommentVisible; expected_visible_comment="${Ts741InvalidDomainScopeRepository.initialComment}"; unexpected_visible_comment="${Ts741InvalidDomainScopeRepository.hiddenUpdatedComment}"; visible_texts=${_formatSnapshot(visibleTextsAfterSync)}',
        );
        _recordHumanVerification(
          result,
          check:
              'Confirmed the selected issue detail surface stayed on screen and the Comments tab content was not visibly replaced after sync processing.',
          observed:
              'issue_detail_still_visible=$issueDetailStillVisible; visible_semantics=${_formatSnapshot(visibleSemanticsAfterSync)}',
        );

        if (failures.isNotEmpty) {
          throw AssertionError(failures.join('\n\n'));
        }

        _writePassOutputs(result);
      } catch (error, stackTrace) {
        result['error'] = '${error.runtimeType}: $error';
        result['traceback'] = stackTrace.toString();
        result['visible_texts_at_failure'] = screen.visibleTextsSnapshot();
        result['visible_semantics_at_failure'] = screen
            .visibleSemanticsLabelsSnapshot();
        _writeFailureOutputs(result);
        Error.throwWithStackTrace(error, stackTrace);
      } finally {
        screen.resetView();
        semantics.dispose();
      }
    },
    timeout: const Timeout(Duration(seconds: 45)),
  );
}

Directory get _outputsDir => Directory('${Directory.current.path}/outputs');
File get _jiraCommentFile => File('${_outputsDir.path}/jira_comment.md');
File get _prBodyFile => File('${_outputsDir.path}/pr_body.md');
File get _responseFile => File('${_outputsDir.path}/response.md');
File get _resultFile => File('${_outputsDir.path}/test_automation_result.json');
File get _bugDescriptionFile => File('${_outputsDir.path}/bug_description.md');

Future<void> _resumeApp(WidgetTester tester) async {
  tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 250));
  await tester.pumpAndSettle();
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
    "* Published a hosted background sync event whose changed path used an undefined domain scope ({code}${Ts741InvalidDomainScopeRepository.unknownChangedPath}{code}).",
    '* Kept the production TRACK-741C Comments tab open while the workspace sync listener processed the event.',
    '* Verified issue-level hydration stayed suppressed for TRACK-741C and checked that the original visible comment remained unchanged.',
    '',
    'h4. Result',
    passed
        ? "* Matched the expected result: hydration_delta_count stayed at 0 for TRACK-741C, no comments/detail hydration was dispatched, and the original comment remained visible in the Comments tab."
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* Repository: {noformat}${result['repository'] ?? '<missing>'}{noformat}',
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
    '**Status:** $statusLabel',
    '**Test Case:** $_ticketKey - $_ticketSummary',
    '',
    '## What was automated',
    '- Published a hosted background sync event whose changed path used an undefined domain scope.',
    '- Kept the production TRACK-741C Comments tab open while the workspace sync listener processed the event.',
    '- Verified `hydration_delta_count` stayed at `0` for TRACK-741C and checked that the original visible comment remained unchanged.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: no TRACK-741C comments/detail hydration was dispatched, and the original comment remained visible in the Comments tab.'
        : '- Did not match the expected result. See the failed step details and exact error below.',
    '',
    '## Step results',
    ..._markdownStepLines(result),
    '',
    '## Human-style verification',
    ..._markdownHumanVerificationLines(result),
    '',
    '## Test file',
    '```text',
    _testFilePath,
    '```',
    '',
    '## How to run',
    '```bash',
    _runCommand,
    '```',
  ];

  if (!passed) {
    lines.addAll(<String>[
      '',
      '## Exact error',
      '```text',
      '${result['error'] ?? '<missing>'}',
      '',
      '${result['traceback'] ?? '<missing>'}',
      '```',
    ]);
  }

  return '${lines.join('\n')}\n';
}

String _responseSummary(Map<String, Object?> result, {required bool passed}) {
  final buffer = StringBuffer()
    ..writeln('# $_ticketKey')
    ..writeln()
    ..writeln(
      passed
          ? 'Passed: the unknown hosted sync scope was filtered at the issue level, TRACK-741C hydration_delta_count stayed at 0, and the visible Issue-C comment stayed unchanged.'
          : 'Failed: the unknown hosted sync scope still triggered issue hydration or changed visible comment content that should have remained unchanged.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('Repository: `${result['repository'] ?? '<missing>'}`')
    ..writeln(
      'Observed hydration_delta_count: `${result['hydration_delta_count'] ?? '<missing>'}`',
    );

  if (!passed) {
    buffer
      ..writeln()
      ..writeln('Error:')
      ..writeln('```text')
      ..writeln('${result['error'] ?? '<missing>'}')
      ..writeln()
      ..writeln('${result['traceback'] ?? '<missing>'}')
      ..writeln('```');
  }

  return buffer.toString();
}

String _bugDescription(Map<String, Object?> result) {
  final lines = <String>[
    '# Bug Report - $_ticketKey',
    '',
    '## Summary',
    'An unknown hosted sync domain scope still dispatches issue-level hydration and/or replaces the visible TRACK-741C comment instead of being filtered out.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** an undefined or unknown hosted sync domain scope is ignored, `hydration_delta_count` stays `0`, no TRACK-741C comments/detail hydration is dispatched, and the visible comment remains the original text.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Missing/Broken Production Capability',
    '- The production workspace sync domain filter does not fully suppress unknown hosted change paths at the issue level, allowing targeted hydration and/or visible Comments tab replacement to proceed.',
    '',
    '## Exact Error Message or Assertion Failure',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Environment',
    '- URL: local Flutter test execution',
    '- Browser: none',
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '- Repository: `${result['repository'] ?? '<missing>'}`',
    '- Unknown changed path used: `${result['unknown_changed_path'] ?? '<missing>'}`',
    '',
    '## Relevant Logs',
    '```text',
    'Precondition: ${result['precondition'] ?? '<missing>'}',
    'hydration_delta_count: ${result['hydration_delta_count'] ?? '<missing>'}',
    'hydration_scopes_for_issue: ${((result['hydration_scopes_for_issue'] as List<Object?>?) ?? const <Object?>[]).join(', ')}',
    'repository_comment_after_sync: ${result['repository_comment_after_sync'] ?? '<missing>'}',
    'Visible texts after sync: ${_formatSnapshot((result['visible_texts_after_sync'] as List<Object?>?)?.map((value) => value.toString()).toList(growable: false) ?? const <String>[])}',
    'Visible semantics after sync: ${_formatSnapshot((result['visible_semantics_after_sync'] as List<Object?>?)?.map((value) => value.toString()).toList(growable: false) ?? const <String>[])}',
    'Step details:',
    ..._bugLogLines(result),
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '* Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  Observed: {noformat}${step['observed']}{noformat}',
  ];
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  return [
    for (final step in steps)
      '- Step ${step['step']}: ${step['status'] == 'passed' ? '✅' : '❌'} ${step['action']}\n'
          '  - Observed: `${step['observed']}`',
  ];
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const ['* No additional human-style checks were recorded.'];
  }
  return [
    for (final check in checks)
      '* ${check['check']}\n  Observed: {noformat}${check['observed']}{noformat}',
  ];
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ?? const [];
  if (checks.isEmpty) {
    return const ['- No additional human-style checks were recorded.'];
  }
  return [
    for (final check in checks)
      '- ${check['check']}\n  - Observed: `${check['observed']}`',
  ];
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const ['1. No step results were recorded before the failure.'];
  }
  return [
    for (final step in steps)
      '${step['step']}. ${step['action']} ${step['status'] == 'passed' ? '✅' : '❌'}\n'
          '   - Observed: ${step['observed']}',
  ];
}

List<String> _bugLogLines(Map<String, Object?> result) {
  final steps = (result['steps'] as List<Map<String, Object?>>?) ?? const [];
  if (steps.isEmpty) {
    return const <String>['<no step details recorded>'];
  }
  return [
    for (final step in steps)
      'Step ${step['step']}: ${step['status']} | ${step['action']} | ${step['observed']}',
  ];
}

String _actualResultLine(Map<String, Object?> result) {
  final hydrationDeltaCount = result['hydration_delta_count'];
  final initialCommentStillVisible = result['initial_comment_still_visible'];
  final hiddenUpdatedCommentVisible = result['hidden_updated_comment_visible'];
  final issueDetailStillVisible = result['issue_detail_still_visible'];
  return 'the malformed sync produced hydration_delta_count=$hydrationDeltaCount, '
      'initial_comment_still_visible=$initialCommentStillVisible, '
      'hidden_updated_comment_visible=$hiddenUpdatedCommentVisible, '
      'issue_detail_still_visible=$issueDetailStillVisible.';
}

String _formatHydrationCalls(List<Ts741HydrationCall> calls) {
  if (calls.isEmpty) {
    return '<none>';
  }
  return calls
      .map(
        (call) =>
            '${call.issueKey}[${_scopeNames(call.scopes).join(',')}][force=${call.force}]',
      )
      .join(' | ');
}

List<String> _scopeNames(Iterable<dynamic> scopes) {
  return scopes.map((scope) => scope.toString().split('.').last).toList()
    ..sort();
}

String _formatSnapshot(List<String> values, {int limit = 24}) {
  final snapshot = <String>[];
  for (final value in values) {
    final trimmed = value.trim();
    if (trimmed.isEmpty || snapshot.contains(trimmed)) {
      continue;
    }
    snapshot.add(trimmed);
    if (snapshot.length == limit) {
      break;
    }
  }
  if (snapshot.isEmpty) {
    return '<none>';
  }
  return snapshot.join(' | ');
}
