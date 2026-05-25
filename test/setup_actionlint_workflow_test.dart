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

  test('setup repository exposes an actionlint pass gate for non-workflow PRs', () {
    final workflowFile = repositoryFile(
      'trackstate-setup/.github/workflows/actionlint-non-workflow-pr.yml',
    );

    expect(
      workflowFile.existsSync(),
      isTrue,
      reason:
          'trackstate-setup needs a contributor-visible actionlint check for '
          'non-workflow pull requests because actionlint remains required on '
          'the protected main branch.',
    );

    final workflow = workflowFile.readAsStringSync();
    expect(workflow, contains('pull_request_target:'));
    expect(workflow, contains('paths-ignore:'));
    expect(workflow, contains('.github/workflows/**'));
    expect(workflow, contains('jobs:'));
    expect(workflow, contains('name: actionlint'));
  });
}
