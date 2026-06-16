const String browserWorkspaceSwitcherSemanticsIdentifier =
    'trackstate-workspace-switcher';
const String browserWorkspaceSwitcherRowSemanticsIdentifierPrefix =
    'trackstate-workspace-switcher-row-';
const String browserDesktopCreateIssueSemanticsIdentifier =
    'trackstate-desktop-create-issue';
const String browserDesktopAddWorkspaceSemanticsIdentifier =
    'trackstate-desktop-add-workspace';
const String browserDesktopDashboardSemanticsIdentifier =
    'trackstate-desktop-nav-dashboard';
const String browserDesktopBoardSemanticsIdentifier =
    'trackstate-desktop-nav-board';
const String browserDesktopSearchSectionSemanticsIdentifier =
    'trackstate-desktop-nav-search';
const String browserDesktopHierarchySemanticsIdentifier =
    'trackstate-desktop-nav-hierarchy';
const String browserDesktopSettingsSemanticsIdentifier =
    'trackstate-desktop-nav-settings';
const String browserDesktopWorkspaceSwitcherTriggerSemanticsIdentifier =
    'trackstate-desktop-workspace-switcher-trigger';
const String browserDesktopSearchInputSemanticsIdentifier =
    'trackstate-desktop-search-input';

String browserWorkspaceSwitcherRowSemanticsIdentifier(String workspaceId) =>
    '$browserWorkspaceSwitcherRowSemanticsIdentifierPrefix$workspaceId';

class BrowserWorkspaceSwitcherFocusAncestorSnapshot {
  const BrowserWorkspaceSwitcherFocusAncestorSnapshot({
    this.semanticsIdentifier,
    this.textContent,
  });

  final String? semanticsIdentifier;
  final String? textContent;
}

bool browserFocusWithinWorkspaceSwitcher({
  required Iterable<BrowserWorkspaceSwitcherFocusAncestorSnapshot> ancestors,
}) {
  for (final ancestor in ancestors) {
    if (ancestor.semanticsIdentifier?.trim() ==
        browserWorkspaceSwitcherSemanticsIdentifier) {
      return true;
    }
  }
  return false;
}

bool browserFocusWithinWorkspaceSwitcherRow({
  required Iterable<BrowserWorkspaceSwitcherFocusAncestorSnapshot> ancestors,
}) {
  for (final ancestor in ancestors) {
    final semanticsIdentifier = ancestor.semanticsIdentifier?.trim();
    if (semanticsIdentifier == null) {
      continue;
    }
    if (semanticsIdentifier.startsWith(
      browserWorkspaceSwitcherRowSemanticsIdentifierPrefix,
    )) {
      return true;
    }
  }
  return false;
}

bool browserWorkspaceSwitcherShouldPreventDefaultKey({
  required String key,
  required Iterable<BrowserWorkspaceSwitcherFocusAncestorSnapshot> ancestors,
}) {
  switch (key) {
    case 'ArrowDown':
    case 'ArrowUp':
      return browserFocusWithinWorkspaceSwitcher(ancestors: ancestors);
    case 'Home':
    case 'End':
      return browserFocusWithinWorkspaceSwitcherRow(ancestors: ancestors);
    default:
      return false;
  }
}
