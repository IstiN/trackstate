const { test, expect } = require('@playwright/test');
const { enableFlutterSemantics } = require('../accessibility/accessibility_gate');

const repository = 'IstiN/trackstate-setup';
const defaultBranch = 'main';
const retryTargetBranch = 'ts-1023-retry-target';
const primaryWorkspaceDisplayName = 'TrackState setup (main)';
const alternateWorkspaceDisplayName = 'TrackState setup (retry target)';

test.describe('workspace switcher saved selection regression', () => {
  test('browser row click enables Save and switch for a different saved workspace', async ({ page }) => {
    test.slow();

    await seedWorkspaceProfiles(page);

    await page.goto('/');
    await expect(page).toHaveTitle(/TrackState\.AI/);
    await enableFlutterSemantics(page);

    await openWorkspaceSwitcher(page);

    const saveButtonBeforeSelection = await readVisibleButtonState(
      page,
      'Save and switch',
    );
    expect(saveButtonBeforeSelection, 'Save and switch should be visible').not.toBeNull();
    expect(isButtonEnabled(saveButtonBeforeSelection)).toBe(false);

    const rowClickTarget = await resolveSavedWorkspaceRowClickTarget(
      page,
      alternateWorkspaceDisplayName,
    );
    expect(rowClickTarget, 'saved workspace row should be clickable').not.toBeNull();

    await page.mouse.click(rowClickTarget.clickX, rowClickTarget.clickY);

    await expect
      .poll(async () => {
        const state = await readVisibleButtonState(page, 'Save and switch');
        return state ? isButtonEnabled(state) : false;
      })
      .toBe(true);
  });
});

async function seedWorkspaceProfiles(page) {
  await page.addInitScript((state) => {
    const rawState = JSON.stringify(state);
    for (const key of [
      'trackstate.workspaceProfiles.state',
      'flutter.trackstate.workspaceProfiles.state',
    ]) {
      window.localStorage.setItem(key, rawState);
    }
  }, buildWorkspaceState());
}

function buildWorkspaceState() {
  const repositoryId = repository.toLowerCase();
  const primaryWorkspaceId = `hosted:${repositoryId}@${defaultBranch}`;
  const alternateWorkspaceId =
    `hosted:${repositoryId}@${defaultBranch}:${retryTargetBranch}`;

  return {
    activeWorkspaceId: primaryWorkspaceId,
    migrationComplete: true,
    profiles: [
      {
        id: primaryWorkspaceId,
        displayName: primaryWorkspaceDisplayName,
        customDisplayName: primaryWorkspaceDisplayName,
        targetType: 'hosted',
        target: repository,
        defaultBranch,
        writeBranch: defaultBranch,
        lastOpenedAt: '2026-05-24T00:10:00.000Z',
        hostedAccessMode: 'attachmentRestricted',
      },
      {
        id: alternateWorkspaceId,
        displayName: alternateWorkspaceDisplayName,
        customDisplayName: alternateWorkspaceDisplayName,
        targetType: 'hosted',
        target: repository,
        defaultBranch,
        writeBranch: retryTargetBranch,
        lastOpenedAt: '2026-05-24T00:00:00.000Z',
        hostedAccessMode: 'attachmentRestricted',
      },
    ],
  };
}

async function openWorkspaceSwitcher(page) {
  if (await readVisibleButtonState(page, 'Save and switch')) {
    return;
  }

  const trigger = page.getByRole('button', {
    name: /Workspace switcher:/,
  }).first();
  await expect(trigger).toBeVisible({ timeout: 30000 });
  await trigger.click();
  await expect
    .poll(async () => await readVisibleButtonState(page, 'Save and switch'))
    .not.toBeNull();
}

async function readVisibleButtonState(page, label) {
  return await page.evaluate((targetLabel) => {
    const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
    const isVisible = (element) => {
      if (!element) {
        return false;
      }
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      return rect.width > 0
        && rect.height > 0
        && style.visibility !== 'hidden'
        && style.display !== 'none';
    };
    const elements = Array.from(
      document.querySelectorAll('button, flt-semantics[role="button"], [role="button"]'),
    )
      .filter((element, index, all) => all.indexOf(element) === index)
      .filter((element) => isVisible(element))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        const visibleText = normalize(element.innerText || element.textContent || '');
        const accessibleLabel = normalize(
          element.getAttribute('aria-label')
          || element.getAttribute('title')
          || visibleText,
        );
        return {
          visibleText,
          accessibleLabel,
          ariaDisabled: element.getAttribute('aria-disabled'),
          disabled:
            typeof element.disabled === 'boolean'
              ? element.disabled
              : element.hasAttribute('disabled'),
          area: rect.width * rect.height,
        };
      })
      .filter(
        (element) =>
          element.visibleText === targetLabel || element.accessibleLabel === targetLabel,
      )
      .sort((left, right) => right.area - left.area);
    return elements[0] ?? null;
  }, label);
}

function isButtonEnabled(buttonState) {
  return !buttonState.disabled && buttonState.ariaDisabled !== 'true';
}

async function resolveSavedWorkspaceRowClickTarget(page, displayName) {
  return await page.evaluate((targetDisplayName) => {
    const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
    const isVisible = (element) => {
      if (!element) {
        return false;
      }
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      return rect.width > 0
        && rect.height > 0
        && style.visibility !== 'hidden'
        && style.display !== 'none';
    };
    const textFor = (element) => normalize(element?.innerText || element?.textContent || '');
    const labelFor = (element) =>
      normalize(
        element?.getAttribute?.('aria-label')
        || element?.getAttribute?.('title')
        || element?.innerText
        || element?.textContent
        || '',
      );
    const candidates = Array.from(
      document.querySelectorAll(
        [
          '[data-trackstate-browser-focus-row-id]',
          '[data-trackstate-browser-focus-id]',
          '[flt-semantics-identifier]',
          '[aria-current]',
          '[aria-selected]',
          'flt-semantics[role="button"]',
          'button',
          '[role="button"]',
        ].join(','),
      ),
    )
      .filter((element, index, all) => all.indexOf(element) === index)
      .filter((element) => isVisible(element))
      .map((element) => {
        const label = labelFor(element);
        const text = textFor(element);
        const combined = normalize(`${label} ${text}`);
        const focusId = normalize(
          element.getAttribute('data-trackstate-browser-focus-id') || '',
        );
        const rowId = normalize(
          element.getAttribute('data-trackstate-browser-focus-row-id') || '',
        );
        const identifier = normalize(
          element.getAttribute('flt-semantics-identifier') || '',
        );
        const ariaCurrent = normalize(element.getAttribute('aria-current') || '');
        const ariaSelected = normalize(element.getAttribute('aria-selected') || '');
        const isActionButton =
          label.startsWith('Open: ')
          || label.startsWith('Delete: ')
          || text.startsWith('Open: ')
          || text.startsWith('Delete: ')
          || label === 'Active'
          || text === 'Active';
        const rowSpecificId =
          rowId.startsWith('trackstate-workspace-switcher-row-')
          || focusId.startsWith('trackstate-workspace-switcher-row-')
          || identifier.startsWith('trackstate-workspace-switcher-row-');
        const looksLikeCurrentRow =
          ariaCurrent.toLowerCase() === 'true'
          || ariaSelected.toLowerCase() === 'true'
          || combined.includes('Active');
        const matchesDisplayName = combined.includes(targetDisplayName);
        const rowLikeCandidate = rowSpecificId || looksLikeCurrentRow;
        if (
          !matchesDisplayName
          || !rowLikeCandidate
          || isActionButton
          || focusId.includes('trigger')
        ) {
          return null;
        }
        const rect = element.getBoundingClientRect();
        const area = rect.width * rect.height;
        return {
          clickX: rect.left + (rect.width / 2),
          clickY: rect.top + (rect.height / 2),
          score:
            (rowSpecificId ? 1_000_000 : 0)
            + (looksLikeCurrentRow ? 100_000 : 0)
            + (combined.includes('Branch:') ? 10_000 : 0)
            + Math.round(area),
        };
      })
      .filter((candidate) => candidate !== null)
      .sort((left, right) => right.score - left.score);

    return candidates[0] ?? null;
  }, displayName);
}
