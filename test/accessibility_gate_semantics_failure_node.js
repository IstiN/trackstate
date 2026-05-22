const assert = require('node:assert/strict');
const test = require('node:test');
const Module = require('node:module');

const originalLoad = Module._load;
Module._load = function patchedModuleLoad(request, parent, isMain) {
  if (request === '@axe-core/playwright') {
    return {
      AxeBuilder: class AxeBuilder {
        withRules() {
          return this;
        }

        async analyze() {
          return { violations: [] };
        }
      },
    };
  }

  return originalLoad.call(this, request, parent, isMain);
};

const { enableFlutterSemantics } = require('../testing/accessibility/accessibility_gate');

Module._load = originalLoad;

test('enableFlutterSemantics throws a descriptive semantics initialization error', async () => {
  const fakePage = {
    async waitForSelector() {},
    locator() {
      return {
        async evaluate() {},
      };
    },
    async waitForFunction() {
      throw new Error('page.waitForFunction: Test timeout of 120000ms exceeded');
    },
    async evaluate() {
      return {
        placeholderCount: 1,
        hostCount: 1,
        nodeCount: 0,
      };
    },
  };

  await assert.rejects(
    () => enableFlutterSemantics(fakePage),
    (error) => {
      assert.match(
        error.message,
        /Flutter engine failed to render semantics nodes during initialization/,
      );
      assert.match(error.message, /placeholder-count=1/);
      assert.match(error.message, /host-count=1/);
      assert.match(error.message, /node-count=0/);
      assert.doesNotMatch(error.message, /page\.waitForFunction/);
      return true;
    },
  );
});
