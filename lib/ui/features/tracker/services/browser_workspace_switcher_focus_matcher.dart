const String browserWorkspaceSwitcherSemanticsIdentifier =
    'trackstate-workspace-switcher';
const String browserWorkspaceSwitcherRowSemanticsIdentifierPrefix =
    'trackstate-workspace-switcher-row-';

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
