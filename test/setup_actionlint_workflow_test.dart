import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test('setup repository exposes a contributor-visible actionlint gate', () {
    final workflowFile = repositoryFile(
      'trackstate-setup/.github/workflows/actionlint.yml',
    );

    expect(
      workflowFile.existsSync(),
      isTrue,
      reason:
          'trackstate-setup needs a dedicated actionlint workflow so invalid '
          'workflow edits fail with an actionable CI run instead of a generic '
          'workflow-file error.',
    );

    final workflow = workflowFile.readAsStringSync();
    expect(workflow, contains('actionlint'));
    expect(workflow, contains('push:'));
    expect(workflow, contains('pull_request:'));
    expect(workflow, contains('.github/workflows/**'));
    expect(workflow, contains('jobs:'));
    expect(workflow, contains('name: actionlint'));
    expect(workflow, contains('timeout-minutes:'));
    expect(workflow, contains('Enforce job-level timeout-minutes'));
    expect(workflow, contains('Run actionlint'));
  });

  test('setup repository detects workflow file changes on pushes and PRs', () {
    final workflowFile = repositoryFile(
      'trackstate-setup/.github/workflows/actionlint.yml',
    );
    final fallbackWorkflowFile = repositoryFile(
      'trackstate-setup/.github/workflows/actionlint-non-workflow-pr.yml',
    );

    expect(
      workflowFile.existsSync(),
      isTrue,
      reason:
          'trackstate-setup must keep the contributor-visible actionlint '
          'workflow that validates workflow edits before they break release '
          'automation.',
    );
    expect(
      fallbackWorkflowFile.existsSync(),
      isFalse,
      reason:
          'trackstate-setup must keep only one contributor-visible '
          'actionlint workflow so mixed pull requests do not surface '
          'duplicate required checks.',
    );

    final workflow = workflowFile.readAsStringSync();
    expect(workflow, contains('pull_request:'));
    expect(workflow, isNot(contains('pull_request_target:')));
    expect(
      workflow,
      contains('Determine whether workflow files changed'),
    );
    expect(workflow, contains('git diff --name-only'));
    expect(workflow, contains('github.event.before'));
    expect(workflow, contains('github.sha'));
    expect(workflow, contains('git merge-base'));
    expect(workflow, isNot(contains('origin/HEAD')));
    expect(workflow, contains('DEFAULT_BRANCH'));
    expect(workflow, contains('git fetch origin'));
    expect(workflow, contains('.github/workflows/'));
    expect(workflow, contains('No workflow file changes'));
    expect(
      workflow,
      contains("steps.workflow-changes.outputs.changed == 'true'"),
    );
    expect(workflow, isNot(contains('if: github.event_name == \'pull_request\'')));
    expect(workflow, isNot(contains('if: github.event_name != \'pull_request\'')));
    expect(workflow, contains('fetch-depth: 0'));
    expect(
      workflow,
      contains(
        'Skipping actionlint because this run does not modify '
        '.github/workflows/.',
      ),
    );
  });

  test(
    'change detection survives a new-branch push without origin/HEAD',
    () async {
      final workflowFile = repositoryFile(
        'trackstate-setup/.github/workflows/actionlint.yml',
      );
      final workflow = workflowFile.readAsStringSync();
      final script = _extractFirstRunScript(workflow);

      final tempDir = await Directory.systemTemp.createTemp('ts-actionlint-');
      try {
        Future<ProcessResult> runGit(List<String> args) => Process.run(
              'git',
              args,
              workingDirectory: tempDir.path,
              runInShell: false,
            );

        await runGit(['init']);
        await runGit(['config', 'user.email', 'test@example.com']);
        await runGit(['config', 'user.name', 'Test User']);

        final readme = File('${tempDir.path}/README.md');
        await readme.writeAsString('# init');
        await runGit(['add', '.']);
        await runGit(['commit', '-m', 'init']);

        await runGit(['checkout', '-b', 'disposable-feature']);
        final workflowPath = '${tempDir.path}/.github/workflows/example.yml';
        await File(workflowPath).create(recursive: true);
        await File(workflowPath).writeAsString(
          'name: example\n'
          'on: push\n'
          'jobs:\n'
          '  example:\n'
          '    runs-on: ubuntu-latest\n'
          '    steps:\n'
          '      - uses: actions/checkout@v6\n',
        );
        await runGit(['add', '.']);
        await runGit(['commit', '-m', 'add workflow']);

        final headResult = await runGit(['rev-parse', 'HEAD']);
        final headSha = (headResult.stdout as String).trim();

        final outputFile = File('${tempDir.path}/github_output');
        final env = Map<String, String>.from(Platform.environment)
          ..['BASE_SHA'] = '0000000000000000000000000000000000000000'
          ..['HEAD_SHA'] = headSha
          ..['GITHUB_OUTPUT'] = outputFile.path;

        final result = await Process.run(
          'bash',
          ['-e', '-c', script],
          workingDirectory: tempDir.path,
          environment: env,
          runInShell: false,
        );

        expect(
          result.exitCode,
          0,
          reason:
              'The change-detection script should not crash when origin/HEAD '
              'and origin/main are absent.\nstdout:\n${result.stdout}\n'
              'stderr:\n${result.stderr}',
        );
        expect(
          outputFile.existsSync(),
          isTrue,
          reason: 'GITHUB_OUTPUT should be written.',
        );
        expect(
          outputFile.readAsStringSync(),
          contains('changed=true'),
          reason: 'A workflow file change must be detected.',
        );
      } finally {
        await tempDir.delete(recursive: true);
      }
    },
  );
}

String _extractFirstRunScript(String workflow) {
  const runMarker = 'run: |';
  final runIndex = workflow.indexOf(runMarker);
  expect(runIndex, greaterThan(-1), reason: 'workflow must contain a run block');

  final lineStart = workflow.lastIndexOf('\n', runIndex) + 1;
  final runIndent = runIndex - lineStart;
  final blockStart = workflow.indexOf('\n', runIndex) + 1;

  final rawLines = workflow.substring(blockStart).split('\n');
  final scriptLines = <String>[];
  int? contentIndent;

  for (final raw in rawLines) {
    if (raw.trim().isEmpty) {
      scriptLines.add('');
      continue;
    }

    final leading = raw.length - raw.trimLeft().length;
    if (leading <= runIndent && raw.trimLeft().startsWith('- ')) {
      break;
    }

    contentIndent ??= leading;
    if (contentIndent > 0 && raw.startsWith(' ' * contentIndent)) {
      scriptLines.add(raw.substring(contentIndent));
    } else {
      scriptLines.add(raw.trimLeft());
    }
  }

  return scriptLines.join('\n');
}
