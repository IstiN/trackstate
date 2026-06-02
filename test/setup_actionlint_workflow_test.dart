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

  test('setup repository keeps a single shipped actionlint PR gate', () {
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
      contains('Determine whether this PR changes workflow files'),
    );
    expect(workflow, contains('git diff --name-only'));
    expect(workflow, contains('.github/workflows/'));
    expect(workflow, contains('No workflow file changes in this pull request'));
    expect(
      workflow,
      contains("steps.workflow-changes.outputs.changed == 'true'"),
    );
    expect(workflow, contains('fetch-depth: 0'));
    expect(
      workflow,
      contains(
        'Skipping actionlint because this pull request does not modify '
        '.github/workflows/.',
      ),
    );
  });
}
