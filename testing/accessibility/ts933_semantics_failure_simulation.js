async function installTs933SemanticsFailureSimulation(page) {
  await page.addInitScript(() => {
    const originalQuerySelectorAll = Document.prototype.querySelectorAll;
    Document.prototype.querySelectorAll = function ts933PatchedQuerySelectorAll(
        selectors,
    ) {
      if (selectors === 'flt-semantics') {
        return originalQuerySelectorAll.call(
            this,
            'flt-ts933-simulated-no-semantics',
        );
      }
      return originalQuerySelectorAll.call(this, selectors);
    };
  });
}

module.exports = {
  installTs933SemanticsFailureSimulation,
};
