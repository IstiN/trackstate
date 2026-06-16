const assert = require('node:assert/strict');
const test = require('node:test');

const {
  captureFlutterStartupDiagnostics,
  enableFlutterSemantics,
} = require('./accessibility_gate');

class FakeLocator {
  async evaluate() {
  }
}

class FakePage {
  constructor() {
    this.calls = [];
  }

  async goto(url) {
    this.calls.push(['goto', url]);
  }

  async waitForLoadState(state) {
    this.calls.push(['waitForLoadState', state]);
  }

  async waitForSelector(selector, options) {
    this.calls.push(['waitForSelector', selector, options]);
  }

  locator(selector) {
    this.calls.push(['locator', selector]);
    return new FakeLocator();
  }

  async waitForFunction(callback) {
    this.calls.push(['waitForFunction', callback.toString()]);
  }

  async evaluate(callback) {
    this.calls.push(['evaluate', callback.toString()]);
    return {
      hostCount: 1,
      nodeCount: 5,
      sampleLabels: ['Create tracker'],
    };
  }
}

test(
    'captureFlutterStartupDiagnostics records engine transitions and semantics discovery states',
    async () => {
      const page = new FakePage();
      const observedLogs = [];

      const diagnostics = await captureFlutterStartupDiagnostics(page, {
        log: (entry) => observedLogs.push(entry),
      });

      assert.deepEqual(diagnostics.engineEntries, [
        'Flutter engine initialization: bootstrap requested',
        'Flutter engine initialization: page loaded',
        'Flutter engine initialization: semantics placeholder attached',
        'Flutter engine initialization: semantics host attached',
      ]);
      assert.deepEqual(diagnostics.semanticsEntries, [
        'Semantics tree discovery: waiting for nodes',
        'Semantics tree discovery: verified flt-semantics-placeholder',
        'Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]',
      ]);
      assert.deepEqual(observedLogs, [
        'Flutter engine initialization: bootstrap requested',
        'Flutter engine initialization: page loaded',
        'Semantics tree discovery: waiting for nodes',
        'Semantics tree discovery: verified flt-semantics-placeholder',
        'Flutter engine initialization: semantics placeholder attached',
        'Flutter engine initialization: semantics host attached',
        'Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]',
      ]);
      assert.deepEqual(page.calls.slice(0, 5), [
        ['goto', '/'],
        ['waitForLoadState', 'networkidle'],
        [
          'waitForSelector',
          'flt-semantics-placeholder',
          { state: 'attached', timeout: 15000 },
        ],
        ['locator', 'flt-semantics-placeholder'],
        [
          'waitForSelector',
          'flt-semantics-host',
          { state: 'attached', timeout: 15000 },
        ],
      ]);
      assert.equal(page.calls[5][0], 'waitForFunction');
      assert.equal(page.calls[6][0], 'evaluate');
    },
);

test(
    'captureFlutterStartupDiagnostics logs explicit placeholder verification before runtime readiness',
    async () => {
      const page = new FakePage();
      const observedLogs = [];

      const diagnostics = await captureFlutterStartupDiagnostics(page, {
        log: (entry) => observedLogs.push(entry),
      });

      const placeholderEvidence =
        'Semantics tree discovery: verified flt-semantics-placeholder';
      assert.ok(
          diagnostics.semanticsEntries.includes(placeholderEvidence),
          'Expected semantics diagnostics to include explicit placeholder verification evidence.',
      );

      const placeholderIndex = observedLogs.indexOf(placeholderEvidence);
      const runtimeIndex = observedLogs.indexOf(
          'Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]',
      );
      assert.notEqual(
          placeholderIndex,
          -1,
          'Expected the shared accessibility log to include placeholder verification evidence.',
      );
      assert.notEqual(
          runtimeIndex,
          -1,
          'Expected the shared accessibility log to include runtime readiness evidence.',
      );
      assert.ok(
          placeholderIndex < runtimeIndex,
          'Expected placeholder verification to be logged before runtime readiness evidence.',
      );
    },
);

test(
    'enableFlutterSemantics surfaces a descriptive pre-flight error when the placeholder never appears',
    async () => {
      const timeoutError = new Error(
          'page.waitForSelector: Timeout 15000ms exceeded.',
      );
      timeoutError.name = 'TimeoutError';
      const page = {
        async waitForSelector(selector) {
          if (selector === 'flt-semantics-placeholder') {
            throw timeoutError;
          }
        },
      };

      await assert.rejects(
          () => enableFlutterSemantics(page),
          (error) => {
            assert.match(
                error.message,
                /Accessibility pre-flight failed because flt-semantics-placeholder was missing before the scan could begin/,
            );
            assert.doesNotMatch(error.message, /page\.waitForSelector/i);
            return true;
          },
      );
    },
);
