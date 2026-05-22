async function installTs952MissingPlaceholderSimulation(page) {
  await page.addInitScript(() => {
    const hiddenSelector = 'flt-semantics-placeholder';
    const fallbackSelector = 'flt-ts952-simulated-missing-placeholder';

    function matchesHiddenPlaceholderSelector(selectors) {
      if (typeof selectors !== 'string') {
        return false;
      }
      return selectors
        .split(',')
        .map((selector) => selector.trim())
        .some((selector) => selector === hiddenSelector);
    }

    const originalDocumentQuerySelector = Document.prototype.querySelector;
    const originalDocumentQuerySelectorAll = Document.prototype.querySelectorAll;
    const originalElementQuerySelector = Element.prototype.querySelector;
    const originalElementQuerySelectorAll = Element.prototype.querySelectorAll;

    function removePlaceholders() {
      const matches = Array.from(
        originalDocumentQuerySelectorAll.call(document, hiddenSelector),
      );
      for (const element of matches) {
        element.remove();
      }
    }

    Document.prototype.querySelector = function ts952DocumentQuerySelector(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return null;
      }
      return originalDocumentQuerySelector.call(this, selectors);
    };

    Document.prototype.querySelectorAll = function ts952DocumentQuerySelectorAll(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return originalDocumentQuerySelectorAll.call(this, fallbackSelector);
      }
      return originalDocumentQuerySelectorAll.call(this, selectors);
    };

    Element.prototype.querySelector = function ts952ElementQuerySelector(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return null;
      }
      return originalElementQuerySelector.call(this, selectors);
    };

    Element.prototype.querySelectorAll = function ts952ElementQuerySelectorAll(
        selectors,
    ) {
      if (matchesHiddenPlaceholderSelector(selectors)) {
        return originalElementQuerySelectorAll.call(this, fallbackSelector);
      }
      return originalElementQuerySelectorAll.call(this, selectors);
    };

    const observer = new MutationObserver(() => {
      removePlaceholders();
    });

    function startHidingPlaceholders() {
      removePlaceholders();
      if (document.documentElement) {
        observer.observe(document.documentElement, {
          childList: true,
          subtree: true,
        });
      }
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', startHidingPlaceholders, {
        once: true,
      });
    } else {
      startHidingPlaceholders();
    }
  });
}

module.exports = {
  installTs952MissingPlaceholderSimulation,
};
