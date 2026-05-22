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
const flutterSemanticsPlaceholderSelector = 'flt-semantics-placeholder';
const flutterRuntimeContrastProbeSelector =
  '#trackstate-accessibility-probe-color-contrast'
  + '[data-trackstate-accessibility-probe="color-contrast"]';

function isSemanticsInitializationTimeout(error) {
  if (!(error instanceof Error)) {
    return false;
  }

  const normalizedMessage = error.message.toLowerCase();
  return normalizedMessage.includes('timeout')
    && (
      normalizedMessage.includes('waitforselector')
      || normalizedMessage.includes('waitforfunction')
      || normalizedMessage.includes('test timeout')
    );
}

function formatMissingPlaceholderPreflightError(
    selector = flutterSemanticsPlaceholderSelector,
) {
  return (
    'Accessibility pre-flight failed because '
    + `${selector} was missing before the scan could begin.`
  );
}

async function waitForSemanticsPlaceholder(page) {
  try {
    await page.waitForSelector(flutterSemanticsPlaceholderSelector, {
      state: 'attached',
      timeout: flutterSemanticsInitializationTimeoutMs,
    });
  } catch (error) {
    if (!isSemanticsInitializationTimeout(error)) {
      throw error;
    }
    throw new Error(formatMissingPlaceholderPreflightError());
  }
}

async function enableFlutterSemantics(
    page,
    {
      onPlaceholderReady,
      onHostReady,
    } = {},
) {
  await waitForSemanticsPlaceholder(page);
  onPlaceholderReady?.();
  await page.locator(flutterSemanticsPlaceholderSelector).evaluate((element) => {
    element.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForSelector('flt-semantics-host', {
    state: 'attached',
    timeout: flutterSemanticsInitializationTimeoutMs,
  });
  onHostReady?.();
  try {
    await page.waitForFunction(
      () => document.querySelectorAll('flt-semantics').length > 0,
      undefined,
      { timeout: flutterSemanticsInitializationTimeoutMs },
    );
  } catch (error) {
    if (!isSemanticsInitializationTimeout(error)) {
      throw error;
    }

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
  const flutterRuntimeContrastViolations =
    await collectFlutterRuntimeContrastViolations(page);

  return [
    ...axeResults.violations.map((violation) => ({
      id: violation.id,
      help: violation.help,
      nodes: violation.nodes.map((node) => ({
        target: node.target,
        failureSummary: node.failureSummary,
      })),
    })),
    ...flutterRuntimeContrastViolations,
    ...labelViolations,
  ];
}

async function collectFlutterRuntimeContrastViolations(page) {
  return await page.evaluate(
      ({ selector, defaultThreshold }) => {
        const probes = Array.from(document.querySelectorAll(selector));
        const violations = [];

        for (const probe of probes) {
          const ratio = Number.parseFloat(
              probe.getAttribute('data-trackstate-contrast-ratio') ?? '',
          );
          const threshold = Number.parseFloat(
              probe.getAttribute('data-trackstate-contrast-threshold') ?? '',
          );
          const minimumRatio = Number.isFinite(threshold)
            ? threshold
            : defaultThreshold;
          if (!Number.isFinite(ratio) || ratio >= minimumRatio) {
            continue;
          }

          const foreground =
            probe.getAttribute('data-trackstate-foreground') ?? 'unknown';
          const background =
            probe.getAttribute('data-trackstate-background') ?? 'unknown';
          const text = probe.getAttribute('data-trackstate-text') ?? '';
          const semanticsLabel =
            probe.getAttribute('data-trackstate-semantics-label') ?? '';
          const target = probe.id ? `#${probe.id}` : selector;

          violations.push({
            id: 'color-contrast',
            help: 'Elements must meet minimum color contrast ratio thresholds.',
            nodes: [
              {
                target: [target],
                failureSummary:
                  `Flutter-rendered probe "${text}" with semantics label `
                  + `"${semanticsLabel}" reported contrast ratio `
                  + `${ratio.toFixed(2)}:1 between ${foreground} and `
                  + `${background}, below ${minimumRatio.toFixed(1)}:1.`,
              },
            ],
          });
        }

        return violations;
      },
      {
        selector: flutterRuntimeContrastProbeSelector,
        defaultThreshold: 4.5,
      },
  );
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

function formatFlutterEngineInitializationEvidence(state) {
  return `Flutter engine initialization: ${state}`;
}

function formatSemanticsTreeDiscoveryStatus(status) {
  return `Semantics tree discovery: ${status}`;
}

function formatPlaceholderVerificationEvidence(selector = 'flt-semantics-placeholder') {
  return formatSemanticsTreeDiscoveryStatus(`verified ${selector}`);
}

function appendAccessibilityLog(entries, entry, log) {
  if (entries.at(-1) === entry) {
    return;
  }
  entries.push(entry);
  log(entry);
}

async function captureFlutterStartupDiagnostics(
    page,
    {
      log = () => {},
    } = {},
) {
  const engineEntries = [];
  const semanticsEntries = [];

  appendAccessibilityLog(
      engineEntries,
      formatFlutterEngineInitializationEvidence('bootstrap requested'),
      log,
  );
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  appendAccessibilityLog(
      engineEntries,
      formatFlutterEngineInitializationEvidence('page loaded'),
      log,
  );
  appendAccessibilityLog(
      semanticsEntries,
      formatSemanticsTreeDiscoveryStatus('waiting for nodes'),
      log,
  );

  const semanticsEvidence = await enableFlutterSemantics(page, {
    onPlaceholderReady: () => {
      appendAccessibilityLog(
          semanticsEntries,
          formatPlaceholderVerificationEvidence(),
          log,
      );
      appendAccessibilityLog(
          engineEntries,
          formatFlutterEngineInitializationEvidence(
              'semantics placeholder attached',
          ),
          log,
      );
    },
    onHostReady: () => {
      appendAccessibilityLog(
          engineEntries,
          formatFlutterEngineInitializationEvidence('semantics host attached'),
          log,
      );
    },
  });

  appendAccessibilityLog(
      semanticsEntries,
      formatFlutterSemanticsEvidence(semanticsEvidence),
      log,
  );

  return {
    engineEntries,
    semanticsEntries,
    semanticsEvidence,
  };
}

module.exports = {
  accessibilityGateRules,
  captureFlutterStartupDiagnostics,
  collectAccessibilityViolations,
  collectFlutterRuntimeContrastViolations,
  enableFlutterSemantics,
  isSemanticsInitializationTimeout,
  formatFlutterEngineInitializationEvidence,
  formatMissingPlaceholderPreflightError,
  formatPlaceholderVerificationEvidence,
  formatSemanticsTreeDiscoveryStatus,
  formatFlutterSemanticsEvidence,
  formatViolations,
  readFlutterSemanticsEvidence,
  waitForSemanticsPlaceholder,
};
