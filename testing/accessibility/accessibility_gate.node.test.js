const assert = require('node:assert/strict');
const test = require('node:test');

const {
  captureFlutterStartupDiagnostics,
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
        'Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]',
      ]);
      assert.deepEqual(observedLogs, [
        'Flutter engine initialization: bootstrap requested',
        'Flutter engine initialization: page loaded',
        'Semantics tree discovery: waiting for nodes',
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
