import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import '../../components/services/local_workspace_bootstrap_service.dart';
import '../../core/interfaces/local_workspace_bootstrap_probe.dart';
import '../../core/models/local_workspace_bootstrap_observation.dart';

const String _ticketKey = 'TS-718';
const String _ticketSummary =
    'Initialize folder — minimal scaffold and mandatory commit creation';
const String _testFilePath = 'testing/tests/TS-718/test_ts_718.dart';
const String _runCommand =
    'flutter test testing/tests/TS-718/test_ts_718.dart --reporter expanded';
const String _workspaceName = 'Minimal Local Workspace';
const String _writeBranch = 'main';

const List<String> _requestSteps = <String>[
  "Select 'Initialize folder' on the Onboarding screen.",
  "Pick the empty directory and click 'Initialize here'.",
  'After success, inspect the folder contents using a file manager.',
  "Verify git history using 'git log' in the target folder.",
  'Check project.json for \'attachmentStorage.mode: "repository-path"\' (AC3).',
];

void main() {
  test(
    'TS-718 initialize folder creates the minimal scaffold and first commit',
    () async {
      final result = <String, Object?>{
        'ticket': _ticketKey,
        'ticket_summary': _ticketSummary,
        'environment': 'flutter test',
        'os': Platform.operatingSystem,
        'run_command': _runCommand,
        'steps': <Map<String, Object?>>[],
        'human_verification': <Map<String, Object?>>[],
      };

      final LocalWorkspaceBootstrapProbe probe = LocalWorkspaceBootstrapService();
      Directory? cleanupRoot;

      try {
        final observation = await probe.runScenario(
          workspaceName: _workspaceName,
          writeBranch: _writeBranch,
        );
        cleanupRoot = Directory(observation.targetFolderPath).parent;

        result['target_folder_path'] = observation.targetFolderPath;
        result['inspection_state'] = observation.inspectionState;
        result['inspection_message'] = observation.inspectionMessage;
        result['suggested_workspace_name'] = observation.suggestedWorkspaceName;
        result['needs_git_initialization'] = observation.needsGitInitialization;
        result['project_key'] = observation.projectKey;
        result['non_git_file_paths'] = observation.nonGitFilePaths;
        result['directory_tree'] = observation.directoryTree;
        result['git_log_output'] = observation.gitLogOutput;
        result['git_commit_messages'] = observation.gitCommitMessages;
        result['git_commit_count'] = observation.gitCommitCount;
        result['git_head_branch'] = observation.gitHeadBranch;
        result['project_json'] = observation.projectJson;
        result['gitattributes_content'] = observation.gitattributesContent;
        result['issues_index_content'] = observation.issuesIndexContent;
        result['tombstones_index_content'] = observation.tombstonesIndexContent;

        final expectedFiles = _expectedFiles(observation.projectKey);
        final unexpectedFiles = observation.nonGitFilePaths
            .where((path) => !expectedFiles.contains(path))
            .toList(growable: false);
        final missingFiles = expectedFiles
            .where((path) => !observation.nonGitFilePaths.contains(path))
            .toList(growable: false);
        result['expected_file_paths'] = expectedFiles;
        result['missing_files'] = missingFiles;
        result['unexpected_files'] = unexpectedFiles;

        final failures = <String>[];

        final step1Observed =
            'inspection_state=${observation.inspectionState}; '
            'message=${observation.inspectionMessage}; '
            'needs_git_initialization=${observation.needsGitInitialization}; '
            'has_git_repository=${observation.hasGitRepository}; '
            'suggested_workspace_name=${observation.suggestedWorkspaceName}';
        if (observation.inspectionState != 'readyToInitialize' ||
            !observation.needsGitInitialization ||
            observation.hasGitRepository) {
          _recordStep(
            result,
            step: 1,
            status: 'failed',
            action: _requestSteps[0],
            observed: step1Observed,
          );
          failures.add(
            'Step 1 failed: the production initialize-folder preflight did not treat the new empty directory as ready to initialize.\n'
            'Observed inspection state: ${observation.inspectionState}\n'
            'Observed message: ${observation.inspectionMessage}\n'
            'Observed needsGitInitialization: ${observation.needsGitInitialization}\n'
            'Observed hasGitRepository: ${observation.hasGitRepository}',
          );
        } else {
          _recordStep(
            result,
            step: 1,
            status: 'passed',
            action: _requestSteps[0],
            observed: step1Observed,
          );
        }

        final step2Observed =
            'project_key=${observation.projectKey}; '
            'git_head_branch=${observation.gitHeadBranch}; '
            'git_commit_count=${observation.gitCommitCount}; '
            'git_commit_messages=${observation.gitCommitMessages.join(' | ')}';
        if (observation.gitHeadBranch != _writeBranch ||
            observation.gitCommitCount != 1 ||
            observation.gitCommitMessages.length != 1 ||
            observation.gitCommitMessages.single !=
                'Initialize TrackState workspace') {
          _recordStep(
            result,
            step: 2,
            status: 'failed',
            action: _requestSteps[1],
            observed: step2Observed,
          );
          failures.add(
            "Step 2 failed: clicking 'Initialize here' should create a single first commit on `$_writeBranch` with the TrackState initialization message.\n"
            'Observed branch: ${observation.gitHeadBranch}\n'
            'Observed commit count: ${observation.gitCommitCount}\n'
            'Observed commit messages: ${observation.gitCommitMessages.join(' | ')}\n'
            'Observed git log:\n${observation.gitLogOutput}',
          );
        } else {
          _recordStep(
            result,
            step: 2,
            status: 'passed',
            action: _requestSteps[1],
            observed: step2Observed,
          );
        }

        final step3Observed =
            'missing_files=${missingFiles.join(', ')}; '
            'unexpected_files=${unexpectedFiles.join(', ')}; '
            'directory_tree=${_singleLine(observation.directoryTree)}';
        if (missingFiles.isNotEmpty || unexpectedFiles.isNotEmpty) {
          _recordStep(
            result,
            step: 3,
            status: 'failed',
            action: _requestSteps[2],
            observed: step3Observed,
          );
          failures.add(
            'Step 3 failed: the initialized folder did not match the minimal scaffold expected by the ticket.\n'
            'Missing files: ${missingFiles.join(', ')}\n'
            'Unexpected files: ${unexpectedFiles.join(', ')}\n'
            'Observed directory tree:\n${observation.directoryTree}',
          );
        } else {
          _recordStep(
            result,
            step: 3,
            status: 'passed',
            action: _requestSteps[2],
            observed: step3Observed,
          );
        }

        final step4Observed =
            'git_log=${_singleLine(observation.gitLogOutput)}; '
            'git_commit_count=${observation.gitCommitCount}';
        if (!observation.gitLogOutput.contains('Initialize TrackState workspace') ||
            observation.gitCommitCount != 1) {
          _recordStep(
            result,
            step: 4,
            status: 'failed',
            action: _requestSteps[3],
            observed: step4Observed,
          );
          failures.add(
            "Step 4 failed: `git log` should show a first TrackState initialization commit and no extra history.\n"
            'Observed commit count: ${observation.gitCommitCount}\n'
            'Observed git log:\n${observation.gitLogOutput}',
          );
        } else {
          _recordStep(
            result,
            step: 4,
            status: 'passed',
            action: _requestSteps[3],
            observed: step4Observed,
          );
        }

        final attachmentMode =
            (observation.projectJson['attachmentStorage']
                    as Map<String, Object?>?)?['mode']
                ?.toString();
        final step5Observed =
            'attachment_storage_mode=$attachmentMode; '
            'issues_index=${observation.issuesIndexContent.trim()}; '
            'tombstones_index=${observation.tombstonesIndexContent.trim()}; '
            'gitattributes=${_singleLine(observation.gitattributesContent)}';
        if (attachmentMode != 'repository-path' ||
            observation.issuesIndexContent.trim() != '[]' ||
            observation.tombstonesIndexContent.trim() != '[]' ||
            !_containsRequiredLfsRules(observation.gitattributesContent)) {
          _recordStep(
            result,
            step: 5,
            status: 'failed',
            action: _requestSteps[4],
            observed: step5Observed,
          );
          failures.add(
            'Step 5 failed: the minimal scaffold did not preserve the AC3 repository-path attachment storage or empty index files.\n'
            'Observed project.json:\n${_prettyJson(observation.projectJson)}\n'
            'Observed issues index: ${observation.issuesIndexContent}\n'
            'Observed tombstones index: ${observation.tombstonesIndexContent}\n'
            'Observed .gitattributes:\n${observation.gitattributesContent}',
          );
        } else {
          _recordStep(
            result,
            step: 5,
            status: 'passed',
            action: _requestSteps[4],
            observed: step5Observed,
          );
        }

        _recordHumanVerification(
          result,
          check:
              'Reviewed the initialized folder exactly the way a user would after returning to a file manager.',
          observed:
              'target_folder=${observation.targetFolderPath}; directory_tree=${observation.directoryTree}',
        );
        _recordHumanVerification(
          result,
          check:
              "Reviewed `git log` exactly the way a user would from the initialized folder's terminal.",
          observed: 'git_log=${observation.gitLogOutput}',
        );
        _recordHumanVerification(
          result,
          check:
              'Reviewed the generated project.json and index files to confirm the visible scaffold stayed minimal and repository-path based.',
          observed:
              'project_json=${_prettyJson(observation.projectJson)}; issues_index=${observation.issuesIndexContent.trim()}; tombstones_index=${observation.tombstonesIndexContent.trim()}',
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
        if (cleanupRoot != null && cleanupRoot.existsSync()) {
          cleanupRoot.deleteSync(recursive: true);
        }
      }
    },
    timeout: const Timeout(Duration(seconds: 30)),
  );
}

List<String> _expectedFiles(String projectKey) => <String>[
  '.gitattributes',
  '$projectKey/.trackstate/index/issues.json',
  '$projectKey/.trackstate/index/tombstones.json',
  '$projectKey/config/components.json',
  '$projectKey/config/fields.json',
  '$projectKey/config/i18n/en.json',
  '$projectKey/config/issue-types.json',
  '$projectKey/config/priorities.json',
  '$projectKey/config/resolutions.json',
  '$projectKey/config/statuses.json',
  '$projectKey/config/versions.json',
  '$projectKey/config/workflows.json',
  '$projectKey/project.json',
];

bool _containsRequiredLfsRules(String content) {
  const requiredRules = <String>[
    '*.png filter=lfs diff=lfs merge=lfs -text',
    '*.jpg filter=lfs diff=lfs merge=lfs -text',
    '*.jpeg filter=lfs diff=lfs merge=lfs -text',
    '*.gif filter=lfs diff=lfs merge=lfs -text',
    '*.webp filter=lfs diff=lfs merge=lfs -text',
    '*.pdf filter=lfs diff=lfs merge=lfs -text',
    '*.zip filter=lfs diff=lfs merge=lfs -text',
  ];
  return requiredRules.every(content.contains);
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
    "* Executed the production initialize-folder bootstrap flow against a brand-new empty local directory using workspace name {noformat}$_workspaceName{noformat} on branch {noformat}$_writeBranch{noformat}.",
    '* Verified the initialized folder contents matched the minimal non-Git scaffold exactly, including {noformat}project.json{noformat}, the JSON config catalog files, and {noformat}.trackstate/index/{noformat} empty arrays.',
    "* Verified {noformat}git log{noformat} showed exactly one first commit with the TrackState initialization message and that {noformat}project.json{noformat} persisted {noformat}attachmentStorage.mode = repository-path{noformat}.",
    '',
    'h4. Result',
    passed
        ? '* Matched the expected result: initializing an empty folder created only the minimal TrackState scaffold, the required LFS attributes, and one first commit.'
        : '* Did not match the expected result. See the failed step details and exact error below.',
    '* Environment: {noformat}flutter test / ${Platform.operatingSystem}{noformat}',
    '* URL: local filesystem bootstrap scenario',
    '* Browser: none',
    '* Target folder: {noformat}${result['target_folder_path'] ?? '<missing>'}{noformat}',
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
    '- Executed the production initialize-folder bootstrap flow against a brand-new empty local directory using workspace name `$_workspaceName` on branch `$_writeBranch`.',
    '- Verified the initialized folder contents matched the minimal non-Git scaffold exactly, including `project.json`, the JSON config catalog files, and `.trackstate/index/` empty arrays.',
    '- Verified `git log` showed exactly one first commit with the TrackState initialization message and that `project.json` persisted `attachmentStorage.mode = repository-path`.',
    '',
    '## Result',
    passed
        ? '- Matched the expected result: initializing an empty folder created only the minimal TrackState scaffold, the required LFS attributes, and one first commit.'
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
          ? 'Passed: initializing an empty folder created only the minimal TrackState scaffold, repository-path attachment storage, the required LFS rules, and a first Git commit.'
          : 'Failed: initializing an empty folder did not produce the exact minimal scaffold, commit history, and repository-path metadata expected by the ticket.',
    )
    ..writeln()
    ..writeln('Environment: `flutter test / ${Platform.operatingSystem}`')
    ..writeln('URL: `local filesystem bootstrap scenario`')
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
    'Initializing an empty local folder does not fully create the minimal TrackState scaffold and first commit exactly as required by the onboarding bootstrap flow.',
    '',
    '## Environment',
    '- URL: `local filesystem bootstrap scenario`',
    '- Browser: `none`',
    '- OS: `${Platform.operatingSystem}`',
    '- Run command: `$_runCommand`',
    '- Target folder: `${result['target_folder_path'] ?? '<missing>'}`',
    '',
    '## Steps to Reproduce',
    ..._bugStepLines(result),
    '',
    '## Actual vs Expected',
    '- **Expected:** the empty folder is initialized on `main`, the non-Git file tree contains only the minimal scaffold, `.gitattributes` includes the default LFS rules, `git log` shows exactly one `Initialize TrackState workspace` commit, and `project.json` uses `attachmentStorage.mode = repository-path`.',
    '- **Actual:** ${_actualResultLine(result)}',
    '',
    '## Folder tree observed at failure',
    '```text',
    '${result['directory_tree'] ?? '<missing>'}',
    '```',
    '',
    '## git log observed at failure',
    '```text',
    '${result['git_log_output'] ?? '<missing>'}',
    '```',
    '',
    '## Exact error message or assertion failure',
    '```text',
    '${result['error'] ?? '<missing>'}',
    '',
    '${result['traceback'] ?? '<missing>'}',
    '```',
  ];
  return '${lines.join('\n')}\n';
}

List<String> _jiraStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List<Object?>? ?? const <Object?>[])
          .cast<Map<String, Object?>>();
  return steps
      .map(
        (step) =>
            "* Step ${step['step']} ${step['status'] == 'passed' ? 'passed' : 'failed'}: ${step['action']} Observed: {noformat}${step['observed']}{noformat}",
      )
      .toList(growable: false);
}

List<String> _markdownStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List<Object?>? ?? const <Object?>[])
          .cast<Map<String, Object?>>();
  return steps
      .map(
        (step) =>
            '- ${step['status'] == 'passed' ? '✅' : '❌'} Step ${step['step']}: ${step['action']} Observed: `${step['observed']}`',
      )
      .toList(growable: false);
}

List<String> _jiraHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Object?>? ?? const <Object?>[])
          .cast<Map<String, Object?>>();
  return checks
      .map(
        (check) =>
            "* ${check['check']} Observed: {noformat}${check['observed']}{noformat}",
      )
      .toList(growable: false);
}

List<String> _markdownHumanVerificationLines(Map<String, Object?> result) {
  final checks =
      (result['human_verification'] as List<Object?>? ?? const <Object?>[])
          .cast<Map<String, Object?>>();
  return checks
      .map(
        (check) => '- ${check['check']} Observed: `${check['observed']}`',
      )
      .toList(growable: false);
}

List<String> _bugStepLines(Map<String, Object?> result) {
  final steps =
      (result['steps'] as List<Object?>? ?? const <Object?>[])
          .cast<Map<String, Object?>>();
  final indexed = <int, Map<String, Object?>>{
    for (final step in steps) step['step'] as int: step,
  };
  return List<String>.generate(_requestSteps.length, (index) {
    final stepNumber = index + 1;
    final step = indexed[stepNumber];
    if (step == null) {
      return '$stepNumber. ${_requestSteps[index]} ❌ Not reached because the scenario failed earlier.';
    }
    final passed = step['status'] == 'passed';
    return '$stepNumber. ${_requestSteps[index]} ${passed ? '✅' : '❌'} ${step['observed']}';
  });
}

String _actualResultLine(Map<String, Object?> result) {
  final failedStep =
      ((result['steps'] as List<Object?>? ?? const <Object?>[])
              .cast<Map<String, Object?>>()
              .firstWhere(
                (step) => step['status'] != 'passed',
                orElse: () => <String, Object?>{},
              ))['observed']
          ?.toString();
  if (failedStep == null || failedStep.isEmpty) {
    return 'The exact failure observation was not captured before the test aborted.';
  }
  return failedStep;
}

String _singleLine(Object? value) {
  return '$value'.replaceAll('\n', ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
}

String _prettyJson(Object? value) {
  return const JsonEncoder.withIndent('  ').convert(value);
}
