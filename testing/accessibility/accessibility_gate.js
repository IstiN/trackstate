const { AxeBuilder } = require('@axe-core/playwright');

const accessibilityGateRules = [
  'aria-allowed-attr',
  'aria-command-name',
  'aria-input-field-name',
  'aria-required-attr',
  'aria-valid-attr',
  'aria-valid-attr-value',
  'button-name',
  'color-contrast',
  'input-button-name',
  'link-name',
];

const flutterSemanticsInitializationTimeoutMs = 15000;

async function enableFlutterSemantics(page) {
  await page.waitForSelector('flt-semantics-placeholder', { state: 'attached' });
  await page.locator('flt-semantics-placeholder').evaluate((element) => {
    element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForSelector('flt-semantics-host', {
    state: 'attached',
    timeout: flutterSemanticsInitializationTimeoutMs,
  });
  try {
    await page.waitForFunction(
      () => document.querySelectorAll('flt-semantics').length > 0,
      undefined,
      { timeout: flutterSemanticsInitializationTimeoutMs },
    );
  } catch {
    let evidence;
    try {
      evidence = await readFlutterSemanticsEvidence(page);
    } catch {
      throw new Error(
        'Flutter engine failed to render semantics nodes during initialization. '
        + 'The accessibility gate could not inspect the runtime semantics state '
        + 'after the failure.',
      );
    }
    throw new Error(
      'Flutter engine failed to render semantics nodes during initialization. '
      + `Observed runtime state: placeholder-count=${evidence.placeholderCount}; `
      + `host-count=${evidence.hostCount}; `
      + `node-count=${evidence.nodeCount}; `
      + `sample-labels=${JSON.stringify(evidence.sampleLabels)}.`,
    );
  }
  return await readFlutterSemanticsEvidence(page);
}

async function readFlutterSemanticsEvidence(page) {
  return await page.evaluate(() => {
    const semanticsPlaceholders = document.querySelectorAll(
      'flt-semantics-placeholder',
    );
    const semanticsHosts = document.querySelectorAll('flt-semantics-host');
    const semanticsNodes = Array.from(document.querySelectorAll('flt-semantics'));
    const sampleLabels = semanticsNodes
      .map((element) =>
        element.getAttribute('aria-label') ?? element.textContent ?? '',
      )
      .map((value) => value.replace(/\s+/g, ' ').trim())
      .filter((value) => value.length > 0)
      .slice(0, 5);
    return {
      placeholderCount: semanticsPlaceholders.length,
      hostCount: semanticsHosts.length,
      nodeCount: semanticsNodes.length,
      sampleLabels,
    };
  });
}

async function collectAccessibilityViolations(page) {
  const axeResults = await new AxeBuilder({ page })
      .withRules(accessibilityGateRules)
      .analyze();
  const labelViolations = await collectNonDescriptiveLabelViolations(page);

  return [
    ...axeResults.violations.map((violation) => ({
      id: violation.id,
      help: violation.help,
      nodes: violation.nodes.map((node) => ({
        target: node.target,
        failureSummary: node.failureSummary,
      })),
    })),
    ...labelViolations,
  ];
}

async function collectNonDescriptiveLabelViolations(page) {
  return await page.evaluate(() => {
    const interactiveRoles = new Set([
      'button',
      'checkbox',
      'combobox',
      'link',
      'menuitem',
      'option',
      'radio',
      'searchbox',
      'switch',
      'tab',
      'textbox',
    ]);
    const genericLabelsByRole = {
      button: new Set(['button']),
      checkbox: new Set(['checkbox']),
      combobox: new Set(['combobox']),
      link: new Set(['link']),
      menuitem: new Set(['menu item']),
      option: new Set(['option']),
      radio: new Set(['radio']),
      searchbox: new Set(['searchbox']),
      switch: new Set(['switch']),
      tab: new Set(['tab']),
      textbox: new Set(['input', 'text field', 'textbox']),
    };

    const nodes = Array.from(document.querySelectorAll('*'));
    const violations = [];

    function normalizeText(value) {
      return value.replace(/\s+/g, ' ').trim().toLowerCase();
    }

    function inferRole(element) {
      const explicitRole = element.getAttribute('role');
      if (explicitRole) {
        return explicitRole.trim().toLowerCase();
      }

      switch (element.tagName.toLowerCase()) {
        case 'a':
          return element.hasAttribute('href') ? 'link' : null;
        case 'button':
          return 'button';
        case 'input': {
          const type = (element.getAttribute('type') ?? 'text').toLowerCase();
          if (type === 'button' || type === 'reset' || type === 'submit') {
            return 'button';
          }
          if (type === 'checkbox') {
            return 'checkbox';
          }
          if (type === 'radio') {
            return 'radio';
          }
          return 'textbox';
        }
        case 'select':
          return 'combobox';
        case 'textarea':
          return 'textbox';
        default:
          return null;
      }
    }

    function computeAccessibleName(element) {
      const ariaLabel = element.getAttribute('aria-label');
      if (ariaLabel && ariaLabel.trim().length > 0) {
        return ariaLabel.trim();
      }

      const labelledBy = element.getAttribute('aria-labelledby');
      if (labelledBy) {
        const text = labelledBy
            .split(/\s+/)
            .map((id) => document.getElementById(id))
            .filter((labelElement) => labelElement != null)
            .map((labelElement) => labelElement.textContent ?? '')
            .join(' ')
            .replace(/\s+/g, ' ')
            .trim();
        if (text.length > 0) {
          return text;
        }
      }

      if (
        element.tagName.toLowerCase() === 'input' &&
        ['button', 'reset', 'submit'].includes(
            (element.getAttribute('type') ?? '').toLowerCase(),
        )
      ) {
        const value = element.getAttribute('value');
        if (value && value.trim().length > 0) {
          return value.trim();
        }
      }

      const title = element.getAttribute('title');
      if (title && title.trim().length > 0) {
        return title.trim();
      }

      return (element.textContent ?? '').replace(/\s+/g, ' ').trim();
    }

    function describeTarget(element, role, accessibleName) {
      const tagName = element.tagName.toLowerCase();
      const idSuffix = element.id ? `#${element.id}` : '';
      const ariaLabel = element.getAttribute('aria-label');
      const parts = [`${tagName}${idSuffix}`];
      if (role) {
        parts.push(`role="${role}"`);
      }
      if (ariaLabel) {
        parts.push(`aria-label="${ariaLabel}"`);
      } else if (accessibleName) {
        parts.push(`name="${accessibleName}"`);
      }
      return parts.join(' ');
    }

    for (const element of nodes) {
      if (
        element.hasAttribute('hidden') ||
        element.getAttribute('aria-hidden') === 'true'
      ) {
        continue;
      }

      const role = inferRole(element);
      if (role == null || !interactiveRoles.has(role)) {
        continue;
      }

      const accessibleName = computeAccessibleName(element);
      if (accessibleName.length === 0) {
        continue;
      }

      const normalizedName = normalizeText(accessibleName);
      const genericLabels = genericLabelsByRole[role] ?? new Set([role]);
      if (!genericLabels.has(normalizedName)) {
        continue;
      }

      violations.push({
        id: 'non-descriptive-label',
        help: 'Interactive controls need descriptive accessible names.',
        nodes: [
          {
            target: [describeTarget(element, role, accessibleName)],
            failureSummary:
                `Accessible name "${accessibleName}" is too generic for role "${role}".`,
          },
        ],
      });
    }

    return violations;
  });
}

function formatViolations(violations) {
  if (violations.length === 0) {
    return 'Expected no accessibility violations.';
  }

  return violations
      .map((violation) => {
        const nodes = violation.nodes
            .map((node) => {
              const target = node.target.join(' -> ');
              const summary =
                  node.failureSummary?.replace(/\s+/g, ' ').trim() ?? 'No summary';
              return `      - ${target}: ${summary}`;
            })
            .join('\n');
        return `${violation.id}: ${violation.help}\n${nodes}`;
      })
      .join('\n');
}

function formatFlutterSemanticsEvidence(evidence) {
  const sampleLabels = Array.isArray(evidence?.sampleLabels)
    ? evidence.sampleLabels
    : [];
  return (
    'Accessibility runtime surface ready: '
    + `hosts=${evidence?.hostCount ?? 0}; `
    + `nodes=${evidence?.nodeCount ?? 0}; `
    + `sample-labels=${JSON.stringify(sampleLabels)}`
  );
}

module.exports = {
  accessibilityGateRules,
  collectAccessibilityViolations,
  enableFlutterSemantics,
  formatFlutterSemanticsEvidence,
  formatViolations,
};
