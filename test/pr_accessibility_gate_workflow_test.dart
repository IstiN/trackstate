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
      expect(
        workflow,
        contains('node --test testing/accessibility/log_validation.node.test.js'),
        reason:
            'The PR workflow must execute the workflow-contract regression so '
            'contributors see a failed check when the accessibility job loses '
            'the mandatory log-validation step.',
      );
      expect(workflow, contains('npm run test:a11y'));
      expect(workflow, contains('playwright install --with-deps chromium'));
      expect(workflow, contains('TRACKSTATE_USE_DEMO_REPOSITORY=true'));
      expect(
        workflow,
        contains("if: \${{ always() && steps.changes.outputs.accessibility == 'true' }}"),
        reason:
            'The log-validation step must opt into always() so it still runs '
            'after a failed accessibility scan.',
      );
      expect(
        workflow,
        contains('exit "\$exit_code"'),
        reason:
            'The axe-core scan step must keep its real failure status instead '
            'of forcing the run green before log-validation.',
      );
      expect(
        workflow,
        isNot(contains('\n          exit 0\n')),
        reason:
            'The axe-core scan step must not suppress failures, or the live run '
            'cannot prove that log-validation executes after a failed scan.',
      );

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

  test('pull requests expose a downstream deploy preview gate', () {
    final workflowFile = repositoryFile('.github/workflows/unit-tests.yml');

    expect(workflowFile.existsSync(), isTrue);

    final workflow = workflowFile.readAsStringSync();

    expect(
      workflow,
      contains('deploy-preview:'),
      reason:
          'The PR workflow needs a contributor-visible downstream deploy stage '
          'so accessibility failures visibly block any publish path.',
    );
    expect(workflow, contains('name: Deploy preview'));
    expect(workflow, contains('needs: [flutter-checks, accessibility-checks]'));
    expect(workflow, contains('name: Publish preview'));
  });
}
