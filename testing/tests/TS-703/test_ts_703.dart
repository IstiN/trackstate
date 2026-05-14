import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trackstate/data/repositories/trackstate_repository.dart';
import 'package:trackstate/data/services/workspace_profile_service.dart';
import 'package:trackstate/domain/models/trackstate_models.dart';
import 'package:trackstate/domain/models/workspace_profile_models.dart';

import '../../fixtures/workspace_onboarding_screen_fixture.dart';
import '../TS-704/support/ts704_hosted_workspace_runtime.dart';

const String _ticketKey = 'TS-703';
const String _ticketSummary =
    'Hosted repository capture exposes authenticated discovery with manual fallback';
const String _testFilePath = 'testing/tests/TS-703/test_ts_703.dart';
const String _runCommand =
    'flutter test testing/tests/TS-703/test_ts_703.dart --reporter expanded';

const String _currentWorkspaceRepository = 'owner/current';
const String _currentWorkspaceBranch = 'main';
const String _suggestedRepository = 'owner/authenticated-discovery';
const String _suggestedBranch = 'release';
const String _manualRepository = 'manual-owner/manual-repo';
const String _manualBranch = 'feature/preview-42';
const String _manualWorkspaceId =
    'hosted:manual-owner/manual-repo@feature/preview-42';
const String _manualFallbackHint =
    'Select a repository from the current GitHub session or enter owner/repo manually.';
const String _accessibleRepositoriesHeading = 'Accessible repositories';
const String _branchLabel = 'Branch';
const String _repositoryLabel = 'Repository';

const List<String> _requestSteps = <String>[
  "Navigate to Onboarding and select 'Hosted repository'.",
  'With an active GitHub token, verify the presence of a repository selection list.',
  "Without a dedicated picker choice, use the manual fallback by entering 'owner/repo' directly.",
  'Verify that the Branch field is a free-text input.',
  'Enter repository details and verify the identity preview (owner/repo and branch label).',
];

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
  });

  testWidgets(
    'TS-703 hosted onboarding supports authenticated discovery and manual fallback',
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

      SharedPreferences.setMockInitialValues(const <String, Object>{
        'trackstate.githubToken.workspace.hosted%3Aowner%2Fcurrent%40main':
            'workspace-token',
      });
      final workspaceProfileService = SharedPreferencesWorkspaceProfileService(
        now: () => DateTime.utc(2026, 5, 14, 18, 5, 55),
      );
      final openedRepositories = <String>[];
      const accessibleRepositories = <HostedRepositoryReference>[
        HostedRepositoryReference(
          fullName: _suggestedRepository,
          defaultBranch: _suggestedBranch,
        ),
        HostedRepositoryReference(
          fullName: 'owner/platform-foundation',
          defaultBranch: 'main',
        ),
      ];

      Future<TrackStateRepository> openHostedRepository({
        required String repository,
        required String defaultBranch,
        required String writeBranch,
      }) async {
        openedRepositories.add('$repository@$defaultBranch@$writeBranch');
        return Ts704HostedWorkspaceRepository(
          snapshot: await createTs704Snapshot(
            repository: repository,
            branch: defaultBranch,
          ),
          provider: Ts704HostedProvider(
            repositoryName: repository,
            branch: defaultBranch,
            accessibleRepositories: accessibleRepositories,
          ),
        );
      }

      try {
        await workspaceProfileService.createProfile(
          const WorkspaceProfileInput(
            targetType: WorkspaceProfileTargetType.hosted,
            target: _currentWorkspaceRepository,
            defaultBranch: _currentWorkspaceBranch,
          ),
        );
        final bootstrapSnapshot = await createTs704Snapshot(
          repository: 'bootstrap/bootstrap',
          branch: 'main',
        );

        final screen = await launchWorkspaceOnboardingFixture(
          tester,
          repositoryFactory: () => Ts704HostedWorkspaceRepository(
            snapshot: bootstrapSnapshot,
            provider: Ts704HostedProvider(
              repositoryName: 'bootstrap/bootstrap',
              branch: 'main',
            ),
          ),
          workspaceProfileService: workspaceProfileService,
          openHostedRepository: openHostedRepository,
        );

        try {
          final initialState = screen.captureState();
          result['initial_visible_texts'] = initialState.visibleTexts;
          result['initial_top_bar_access_label'] =
              initialState.repositoryAccessTopBarLabel;

          if (openedRepositories.isEmpty ||
              openedRepositories.first !=
                  '$_currentWorkspaceRepository@$_currentWorkspaceBranch@$_currentWorkspaceBranch') {
            throw AssertionError(
              'Precondition failed: the stored hosted workspace did not open with its connected GitHub session before onboarding started.\n'
              'Observed opened repositories: ${openedRepositories.join(', ')}',
            );
          }

          await screen.openAddWorkspace();
          await screen.chooseHostedRepository();

          final selectionState = screen.captureState();
          result['selection_visible_texts'] = selectionState.visibleTexts;
          result['selection_interactive_labels'] =
              selectionState.interactiveSemanticsLabels;

          final step1Failures = <String>[];
          final requiredSelectionTexts = <String>[
            _repositoryLabel,
            _branchLabel,
            _accessibleRepositoriesHeading,
            _manualFallbackHint,
            _suggestedRepository,
            '$_branchLabel: $_suggestedBranch',
            'owner/platform-foundation',
            '$_branchLabel: main',
          ];
          final missingSelectionTexts = requiredSelectionTexts
              .where((text) => !selectionState.visibleTexts.contains(text))
              .toList(growable: false);
          if (!selectionState.isOnboardingVisible) {
            step1Failures.add(
              'The hosted onboarding form was not visible after choosing "Hosted repository".',
            );
          }
          if (missingSelectionTexts.isNotEmpty) {
            step1Failures.add(
              'The authenticated hosted onboarding form did not show the expected repository discovery and manual fallback copy.\n'
              'Missing texts: ${missingSelectionTexts.join(', ')}\n'
              'Observed visible texts: ${selectionState.visibleTexts.join(' | ')}',
            );
          }
          _recordStep(
            result,
            step: 1,
            status: step1Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[0],
            observed:
                'onboarding_visible=${selectionState.isOnboardingVisible}; visible_texts=${selectionState.visibleTexts.join(' || ')}',
          );
          _recordStep(
            result,
            step: 2,
            status: step1Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[1],
            observed:
                'accessible_list_visible=${selectionState.visibleTexts.contains(_accessibleRepositoriesHeading)}; helper_visible=${selectionState.visibleTexts.contains(_manualFallbackHint)}; visible_texts=${selectionState.visibleTexts.join(' || ')}',
          );
          if (step1Failures.isNotEmpty) {
            throw AssertionError(step1Failures.join('\n'));
          }

          await screen.chooseHostedRepositorySuggestion(_suggestedRepository);
          final suggestedState = screen.captureState();
          result['suggested_repository_value'] =
              suggestedState.hostedRepositoryValue;
          result['suggested_branch_value'] = suggestedState.hostedBranchValue;

          if (suggestedState.hostedRepositoryValue != _suggestedRepository ||
              suggestedState.hostedBranchValue != _suggestedBranch ||
              !suggestedState.visibleTexts.contains(
                '$_branchLabel: $_suggestedBranch',
              )) {
            throw AssertionError(
              'Step 5 failed: selecting the authenticated repository suggestion did not keep the expected owner/repo and branch identity visible to the user.\n'
              'Observed repository field: ${suggestedState.hostedRepositoryValue}\n'
              'Observed branch field: ${suggestedState.hostedBranchValue}\n'
              'Observed visible texts: ${suggestedState.visibleTexts.join(' | ')}',
            );
          }

          await screen.enterHostedRepository(_manualRepository);
          await screen.enterHostedBranch(_manualBranch);
          final manualState = screen.captureState();
          result['manual_repository_value'] = manualState.hostedRepositoryValue;
          result['manual_branch_value'] = manualState.hostedBranchValue;
          result['manual_primary_action_label'] =
              manualState.primaryActionLabel;
          result['manual_primary_action_enabled'] =
              manualState.isPrimaryActionEnabled;

          final step3Failures = <String>[];
          if (manualState.hostedRepositoryValue != _manualRepository) {
            step3Failures.add(
              'The hosted repository field did not retain the manual owner/repo fallback value.\n'
              'Observed repository field: ${manualState.hostedRepositoryValue}',
            );
          }
          if (manualState.hostedBranchValue != _manualBranch) {
            step3Failures.add(
              'The Branch field did not retain the custom free-text value.\n'
              'Observed branch field: ${manualState.hostedBranchValue}',
            );
          }
          if (!manualState.visibleTexts.contains(_repositoryLabel) ||
              !manualState.visibleTexts.contains(_branchLabel)) {
            step3Failures.add(
              'The hosted onboarding form did not keep the Repository and Branch labels visible while entering manual fallback values.\n'
              'Observed visible texts: ${manualState.visibleTexts.join(' | ')}',
            );
          }
          _recordStep(
            result,
            step: 3,
            status: step3Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[2],
            observed:
                'repository_value=${manualState.hostedRepositoryValue}; helper_visible=${manualState.visibleTexts.contains(_manualFallbackHint)}; primary_action=${manualState.primaryActionLabel}; primary_action_enabled=${manualState.isPrimaryActionEnabled}',
          );
          _recordStep(
            result,
            step: 4,
            status: step3Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[3],
            observed:
                'branch_value=${manualState.hostedBranchValue}; branch_label_visible=${manualState.visibleTexts.contains(_branchLabel)}',
          );
          _recordStep(
            result,
            step: 5,
            status: step3Failures.isEmpty ? 'passed' : 'failed',
            action: _requestSteps[4],
            observed:
                'repository_value=${manualState.hostedRepositoryValue}; branch_value=${manualState.hostedBranchValue}; repository_label_visible=${manualState.visibleTexts.contains(_repositoryLabel)}; branch_label_visible=${manualState.visibleTexts.contains(_branchLabel)}',
          );
          if (step3Failures.isNotEmpty) {
            throw AssertionError(step3Failures.join('\n'));
          }

          await screen.submit();

          final postOpenState = screen.captureState();
          final workspaceState = await workspaceProfileService.loadState();
          result['opened_repositories'] = openedRepositories;
          result['dashboard_visible'] = postOpenState.isDashboardVisible;
          result['onboarding_visible_after_submit'] =
              postOpenState.isOnboardingVisible;
          result['active_workspace_id'] = workspaceState.activeWorkspaceId;
          result['active_workspace_target'] =
              workspaceState.activeWorkspace?.target;
          result['active_workspace_default_branch'] =
              workspaceState.activeWorkspace?.defaultBranch;
          result['active_workspace_write_branch'] =
              workspaceState.activeWorkspace?.writeBranch;

          if (openedRepositories.last !=
                  '$_manualRepository@$_manualBranch@$_manualBranch' ||
              workspaceState.activeWorkspaceId != _manualWorkspaceId ||
              workspaceState.activeWorkspace?.target != _manualRepository ||
              workspaceState.activeWorkspace?.defaultBranch != _manualBranch ||
              workspaceState.activeWorkspace?.writeBranch != _manualBranch ||
              !postOpenState.isDashboardVisible ||
              postOpenState.isOnboardingVisible) {
            throw AssertionError(
              'Submitting the manual hosted fallback values did not open the expected workspace.\n'
              'Observed opened repositories: ${openedRepositories.join(', ')}\n'
              'Observed active workspace id: ${workspaceState.activeWorkspaceId}\n'
              'Observed active workspace target: ${workspaceState.activeWorkspace?.target}\n'
              'Observed active workspace default branch: ${workspaceState.activeWorkspace?.defaultBranch}\n'
              'Observed active workspace write branch: ${workspaceState.activeWorkspace?.writeBranch}\n'
              'Observed dashboard visible: ${postOpenState.isDashboardVisible}\n'
              'Observed onboarding visible: ${postOpenState.isOnboardingVisible}',
            );
          }

          _recordHumanVerification(
            result,
            check:
                'Verified the hosted onboarding sheet the way an authenticated user would see it: the screen exposed a repository selector, showed repository buttons with branch labels, and also kept the manual owner/repo fallback helper text visible.',
            observed:
                'accessible_list_visible=${selectionState.visibleTexts.contains(_accessibleRepositoriesHeading)}; suggested_repository_visible=${selectionState.visibleTexts.contains(_suggestedRepository)}; suggested_branch_label_visible=${selectionState.visibleTexts.contains('$_branchLabel: $_suggestedBranch')}; fallback_hint_visible=${selectionState.visibleTexts.contains(_manualFallbackHint)}',
          );
          _recordHumanVerification(
            result,
            check:
                'Verified the manual fallback path from the user perspective by typing a custom owner/repo and free-text branch, confirming those exact values stayed visible in the labeled form fields, and opening the workspace with them.',
            observed:
                'repository_field=${manualState.hostedRepositoryValue}; branch_field=${manualState.hostedBranchValue}; repository_label_visible=${manualState.visibleTexts.contains(_repositoryLabel)}; branch_label_visible=${manualState.visibleTexts.contains(_branchLabel)}; active_workspace=${workspaceState.activeWorkspace?.target}@${workspaceState.activeWorkspace?.defaultBranch}',
          );

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
    timeout: const Timeout(Duration(seconds: 30)),
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
    '* Seeded the production hosted workspace state with an active GitHub-backed workspace for {noformat}$_currentWorkspaceRepository{noformat} on {noformat}$_currentWorkspaceBranch{noformat}.',
    '* Opened Add workspace, switched the onboarding flow to {noformat}Hosted repository{noformat}, and verified the authenticated repository discovery list plus the manual fallback helper copy.',
    '* Selected the visible {noformat}$_suggestedRepository{noformat} suggestion and verified the visible branch identity label {noformat}$_branchLabel: $_suggestedBranch{noformat}.',
    '* Entered manual fallback values {noformat}$_manualRepository{noformat} and {noformat}$_manualBranch{noformat}, then clicked {noformat}Open{noformat} and verified the production WorkspaceProfileService opened {noformat}$_manualWorkspaceId{noformat}.',
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: authenticated discovery and manual hosted fallback were both available, the Branch field accepted free-text input, and the exact manual repository details were used when the workspace opened.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* URL: local Flutter widget runtime',
    '* Browser: none',
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
    '- Seeded the production hosted workspace state with an active GitHub-backed workspace for `$_currentWorkspaceRepository` on `$_currentWorkspaceBranch`.',
    '- Opened Add workspace, switched the onboarding flow to `Hosted repository`, and verified the authenticated repository discovery list plus the manual fallback helper copy.',
    '- Selected the visible `$_suggestedRepository` suggestion and verified the visible branch identity label `$_branchLabel: $_suggestedBranch`.',
    '- Entered manual fallback values `$_manualRepository` and `$_manualBranch`, then clicked `Open` and verified the production `WorkspaceProfileService` opened `$_manualWorkspaceId`.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: authenticated discovery and manual hosted fallback were both available, the Branch field accepted free-text input, and the exact manual repository details were used when the workspace opened.'
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
          ? 'Passed: hosted onboarding showed authenticated repository discovery, preserved the manual owner/repo fallback, accepted a free-text branch, and opened the workspace with the exact manual details.'
          : 'Failed: hosted onboarding did not expose authenticated discovery and manual fallback exactly as expected.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('URL: `local Flutter widget runtime`')
    ..writeln('Run command: `$_runCommand`');

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
    'The hosted repository onboarding flow does not fully expose or honor authenticated repository discovery and manual fallback entry the way the ticket requires.',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** after selecting `Hosted repository`, an authenticated user should see a repository selector plus manual `owner/repo` fallback, the `Branch` field should accept free-text input, and opening the workspace with `$_manualRepository` on `$_manualBranch` should use those exact values.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
    '',
    '## Environment',
    '- URL: local Flutter widget runtime',
    '- Browser: none',
    '- OS: ${Platform.operatingSystem}',
    '- Run command: `$_runCommand`',
    '',
    '## Logs',
    '```json',
    const JsonEncoder.withIndent('  ').convert(result),
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
  return steps
      .map(
        (step) =>
            '* Step ${step['step']} - *${step['status']}* - ${step['action']}\n'
            '  **Observed:** ${step['observed']}',
      )
      .toList(growable: false);
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
  return steps
      .map(
        (step) =>
            '- **Step ${step['step']} (${step['status']})** ${step['action']}\n'
            '  - Observed: ${step['observed']}',
      )
      .toList(growable: false);
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
  if (checks.isEmpty) {
    return const <String>[
      '* No additional human-style verification was recorded.',
    ];
  }
  return checks
      .map(
        (check) =>
            '* ${check['check']}\n'
            '  **Observed:** ${check['observed']}',
      )
      .toList(growable: false);
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
  if (checks.isEmpty) {
    return const <String>[
      '- No additional human-style verification was recorded.',
    ];
  }
  return checks
      .map(
        (check) =>
            '- ${check['check']}\n'
            '  - Observed: ${check['observed']}',
      )
      .toList(growable: false);
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List<Map<String, Object?>>?) ??
      const <Map<String, Object?>>[];
  if (steps.isEmpty) {
    return _requestSteps
        .asMap()
        .entries
        .map(
          (entry) => '${entry.key + 1}. ${entry.value} — outcome unavailable.',
        )
        .toList(growable: false);
  }
  return steps
      .map(
        (step) =>
            '${step['step']}. ${step['action']} — ${step['status'] == 'passed' ? 'Passed ✅' : 'Failed ❌'}\n'
            '   Observed: ${step['observed']}',
      )
      .toList(growable: false);
}

String _actualResultLine(Map<String, Object?> result) {
  final failedStep =
      ((result['steps'] as List<Map<String, Object?>>?) ?? const [])
          .cast<Map<String, Object?>>()
          .firstWhere(
            (step) => step['status'] == 'failed',
            orElse: () => const <String, Object?>{},
          );
  if (failedStep.isNotEmpty) {
    return 'Step ${failedStep['step']} failed while checking "${failedStep['action']}". Observed: ${failedStep['observed']}';
  }
  return 'The test failed before a detailed step observation was recorded.';
}
