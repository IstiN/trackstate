const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const workflowPath = path.resolve(__dirname, '../../.github/workflows/unit-tests.yml');

test(
    'accessibility workflow exposes a contributor-visible log-validation step',
    () => {
      const workflowSource = fs.readFileSync(workflowPath, 'utf8');

      const accessibilityCheckIndex = workflowSource.indexOf(
          '- name: Run axe-core accessibility checks',
      );
      const logValidationIndex = workflowSource.indexOf('- name: log-validation');

      assert.notEqual(
          accessibilityCheckIndex,
          -1,
          'Expected the accessibility workflow to run the axe-core scan step.',
      );
      assert.notEqual(
          logValidationIndex,
          -1,
          'Expected the accessibility workflow to expose a contributor-visible `log-validation` step.',
      );
      assert.ok(
          logValidationIndex > accessibilityCheckIndex,
          'Expected `log-validation` to run after the axe-core accessibility scan.',
      );
      assert.match(
          workflowSource,
          /- name: log-validation[\s\S]*node testing\/accessibility\/log_validation\.js/m,
          'Expected the `log-validation` step to invoke the accessibility log validator.',
      );
    },
);

test('validateAccessibilityLog reports missing engine-state tokens', () => {
  const { validateAccessibilityLog } = require('./log_validation');

  assert.throws(
      () => validateAccessibilityLog('> playwright test\nAll tests passed.\n'),
      /mandatory engine state tokens were not found/i,
  );
});

test('validateAccessibilityLog accepts complete Flutter startup diagnostics', () => {
  const { validateAccessibilityLog } = require('./log_validation');

  assert.doesNotThrow(() => validateAccessibilityLog([
    'Flutter engine initialization: bootstrap requested',
    'Semantics tree discovery: waiting for nodes',
    'Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]',
  ].join('\n')));
});
