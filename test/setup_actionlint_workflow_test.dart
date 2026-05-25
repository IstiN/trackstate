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
    expect(workflow, contains('Run actionlint'));
  });

  test('setup repository uses a single actionlint workflow for all PRs', () {
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
          'trackstate-setup needs one contributor-visible actionlint workflow '
          'that can handle both workflow and non-workflow pull requests.',
    );
    expect(
      fallbackWorkflowFile.existsSync(),
      isFalse,
      reason:
          'trackstate-setup must not publish a second actionlint workflow for '
          'non-workflow pull requests because mixed PRs would surface two '
          'ambiguous actionlint checks.',
    );

    final workflow = workflowFile.readAsStringSync();
    expect(workflow, contains('pull_request:'));
    expect(workflow, isNot(contains('pull_request_target:')));
    expect(
      workflow,
      contains('Determine whether this PR changes workflow files'),
    );
    expect(workflow, contains('git diff --name-only'));
    expect(workflow, contains('.github/workflows/'));
    expect(workflow, contains('No workflow file changes in this pull request'));
    expect(
      workflow,
      contains("steps.workflow-changes.outputs.changed == 'true'"),
    );
  });
}
