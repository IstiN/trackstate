import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  File repositoryFile(String relativePath) =>
      File('${Directory.current.path}/$relativePath');

  test(
    'pull requests wire the accessibility gate to executable contrast and semantic regressions',
    () {
      final workflowFile = repositoryFile('.github/workflows/unit-tests.yml');
      final gateHelperFile = repositoryFile(
        'testing/accessibility/accessibility_gate.js',
      );
      final regressionSuiteFile = repositoryFile(
        'testing/accessibility/accessibility_gate_regressions.spec.js',
      );

      expect(
        workflowFile.existsSync(),
        isTrue,
        reason: 'PR validation must live in the required-check workflow.',
      );

      final workflow = workflowFile.readAsStringSync();
      final gateHelper = gateHelperFile.readAsStringSync();
      final regressionSuite = regressionSuiteFile.readAsStringSync();

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

      expect(
        gateHelperFile.existsSync(),
        isTrue,
        reason:
            'The accessibility job should call shared runtime gate logic instead '
            'of relying only on workflow string matching.',
      );
      expect(
        regressionSuiteFile.existsSync(),
        isTrue,
        reason:
            'The repo needs executable Playwright regressions for the ticket '
            'failure modes.',
      );
      expect(gateHelper, contains("id: 'non-descriptive-label'"));
      expect(gateHelper, contains("'color-contrast'"));
      expect(
        regressionSuite,
        contains("expect.objectContaining({ id: 'non-descriptive-label' })"),
      );
      expect(
        regressionSuite,
        contains("expect.objectContaining({ id: 'color-contrast' })"),
      );
    },
  );
}
