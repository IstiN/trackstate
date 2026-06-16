class BrowserFocusableControlDomConfig {
  const BrowserFocusableControlDomConfig({
    required this.tabIndex,
    required this.ariaDisabled,
  });

  final int tabIndex;
  final String? ariaDisabled;
}

BrowserFocusableControlDomConfig resolveBrowserFocusableControlDomConfig({
  required bool enabled,
  required bool focusableWhenDisabled,
  int? explicitTabIndex,
}) {
  return BrowserFocusableControlDomConfig(
    tabIndex:
        explicitTabIndex ?? ((enabled || focusableWhenDisabled) ? 0 : -1),
    ariaDisabled: enabled ? null : 'true',
  );
}
