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

  test('setup repository keeps the shipped actionlint PR gates aligned', () {
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
          'workflow that validates workflow pull requests.',
    );
    expect(
      fallbackWorkflowFile.existsSync(),
      isTrue,
      reason:
          'the shipped setup-repo revision still uses a fallback actionlint '
          'gate for non-workflow pull requests, so this regression test must '
          'stay aligned with the pinned gitlink.',
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

    final fallbackWorkflow = fallbackWorkflowFile.readAsStringSync();
    expect(fallbackWorkflow, contains('pull_request_target:'));
    expect(fallbackWorkflow, contains('paths-ignore:'));
    expect(fallbackWorkflow, contains('.github/workflows/**'));
    expect(fallbackWorkflow, contains('name: actionlint'));
    expect(fallbackWorkflow, contains('Confirm non-workflow PR'));
  });
}
