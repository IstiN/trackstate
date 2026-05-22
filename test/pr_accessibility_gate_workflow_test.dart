import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test('pull requests expose a contributor-visible accessibility gate', () {
    final workflowFile = repositoryFile('.github/workflows/unit-tests.yml');

    expect(
      workflowFile.existsSync(),
      isTrue,
      reason: 'PR validation must live in the required-check workflow.',
    );

    final workflow = workflowFile.readAsStringSync();

    expect(
      workflow,
      contains('accessibility-checks:'),
      reason:
          'The PR workflow needs a dedicated accessibility job so contributors '
          'see a specific failing check instead of only generic Flutter checks.',
    );
    expect(workflow, contains('name: Accessibility checks'));
    expect(workflow, contains('npm ci'));
    expect(workflow, contains('npm run test:a11y'));
    expect(workflow, contains('playwright install --with-deps chromium'));
    expect(workflow, contains('TRACKSTATE_USE_DEMO_REPOSITORY=true'));
  });
}
