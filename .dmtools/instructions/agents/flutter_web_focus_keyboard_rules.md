# Flutter Web Focus & Keyboard Navigation Rules

Injected via `.dmtools/config.js → additionalInstructions`. Addresses recurring BLOCKING review issues in keyboard/focus/accessibility PRs.

## Architecture — Flutter focus vs Browser DOM focus

```mermaid
graph TD
  subgraph Flutter["Flutter Engine (Dart)"]
    FT[FocusTraversalPolicy]
    FS[FocusScopeNode]
    FN[FocusNode]
    CS[CallbackShortcuts]
    Sem[Semantics widget]
  end

  subgraph Browser["Browser DOM (Web only)"]
    TI[tabindex attribute]
    FLTD["flt-semantics DOM nodes"]
    KE[KeyboardEvent]
  end

  Sem -->|"exports"| FLTD
  FN -->|"maps to"| TI
  CS -->|"handles"| KE

  style Flutter fill:#e8f4fd,stroke:#1a73e8
  style Browser fill:#fef7e0,stroke:#f9ab00
```

**Critical insight**: Flutter widget tests exercise the `Flutter Engine` layer only. The `Browser DOM` layer can diverge. A widget test passing does NOT prove the browser keyboard path works.

## Decision tree — Fixing a keyboard/focus bug

```mermaid
flowchart TD
  Start([Bug: keyboard navigation broken]) --> Where{Where does it fail?}
  Where -->|Widget test| WidgetFix[Fix FocusNode/Semantics/Shortcuts in Dart]
  Where -->|Browser only| BrowserAnalyze{Is the Dart Semantics<br/>export correct?}
  BrowserAnalyze -->|No| FixSemantics[Fix Semantics widget props<br/>focusable/selected/sortKey]
  BrowserAnalyze -->|Yes| DOMGap[Flutter web engine gap:<br/>DOM doesn't reflect Dart state]
  DOMGap --> BridgeNeeded{Can we fix via<br/>DOM bridge?}
  BridgeNeeded -->|Yes| DOMBridge[Add browser_*_focus_monitor_web.dart<br/>sync function]
  BridgeNeeded -->|No| Escalate[Document gap in bug_description.md<br/>→ needs Flutter engine fix]

  WidgetFix --> Verify
  FixSemantics --> Verify
  DOMBridge --> Verify

  Verify{Verify fix}
  Verify --> WidgetTest[✅ Widget test for Dart layer]
  Verify --> BrowserTest[✅ Playwright test for DOM layer]
  WidgetTest --> Both[Both must pass]
  BrowserTest --> Both
```

## Anti-pattern #1 — Duplicate event handlers (racing)

**Problem**: Adding a browser-level `window.onKeyDown` handler for a key that Flutter already handles via `CallbackShortcuts` or `KeyboardListener`.

```mermaid
sequenceDiagram
  participant User as User presses ArrowDown
  participant DOM as Browser DOM
  participant Bridge as browser_focus_monitor_web.dart
  participant Flutter as Flutter CallbackShortcuts

  User->>DOM: keydown: ArrowDown
  DOM->>Bridge: window.onKeyDown fires
  Bridge->>Flutter: _switchToAdjacentWorkspace(+1)
  DOM->>Flutter: Flutter engine receives same key
  Flutter->>Flutter: CallbackShortcuts fires
  Flutter->>Flutter: _switchToAdjacentWorkspace(+1) ← AGAIN!
  Note over Flutter: ❌ Double navigation!
```

### Rule: One handler per key per context

```mermaid
flowchart TD
  Key([Key needs handling]) --> FocusOwner{Who owns focus<br/>when key fires?}
  FocusOwner -->|Flutter FocusNode| UseDart[Handle in CallbackShortcuts<br/>or KeyboardListener in Dart]
  FocusOwner -->|Browser DOM node| UseBridge[Handle in browser_*_monitor_web.dart<br/>via window.onKeyDown]
  FocusOwner -->|Both possible| Guard[Add mutual exclusion guard:<br/>check actual focus owner before dispatch]

  UseDart --> NoWeb[❌ Do NOT add duplicate window.onKeyDown]
  UseBridge --> NoDart[❌ Do NOT add duplicate CallbackShortcuts]
```

**Implementation pattern:**
```dart
// ✅ CORRECT — single handler with context check
void _handleBrowserKeyDown(html.KeyboardEvent event) {
  if (!isBrowserFocusOnWorkspaceSwitcherRow()) return; // guard
  if (event.key == 'ArrowDown') {
    event.preventDefault();
    _switchToAdjacentWorkspace(1);
  }
}

// ❌ WRONG — browser handler + Flutter CallbackShortcuts both handle ArrowDown
// This causes double-fire when focus transitions between layers
```

## Anti-pattern #2 — Fixing focus order by removing other elements

**Problem**: Using `ExcludeFocus`, `skipTraversal: true`, or `canRequestFocus: false` on visible interactive elements to "fix" the order of a different element.

```mermaid
flowchart TD
  Bug([Bug: Element X not in tab order]) --> Wrong{Fix approach}
  Wrong -->|"❌ WRONG"| Exclude[ExcludeFocus on element Y<br/>to make X appear 'next']
  Wrong -->|"✅ CORRECT"| Order[FocusTraversalOrder on X<br/>to place it in correct position]

  Exclude --> Breaks[Breaks: Element Y now<br/>unreachable by keyboard]
  Order --> Works[Works: All elements remain<br/>keyboard-accessible]
```

### Rule: Never remove keyboard access from visible interactive elements

Before submitting a focus-order fix, verify:
1. **All previously-focusable elements** in the same area are still keyboard-reachable
2. **The fix adds/reorders**, never removes, focus targets
3. **Check adjacent controls**: theme toggle, sync pill, CTAs, search — all must stay in tab order

```dart
// ❌ WRONG — hides theme toggle from keyboard to "fix" switcher position
ExcludeFocus(child: themeToggleButton)

// ✅ CORRECT — explicit ordering keeps all elements reachable
FocusTraversalOrder(
  order: NumericFocusOrder(3.0),
  child: themeToggleButton,
)
```

## Anti-pattern #3 — Widget test covers metadata, not interaction

**Problem**: Test checks that semantics identifiers/sort keys exist, but doesn't exercise the actual user interaction that fails.

```mermaid
flowchart TD
  Test([Writing regression test]) --> What{What to assert?}
  What -->|"❌ Weak"| Meta[Assert identifier exists<br/>Assert sort key value<br/>Assert node count]
  What -->|"✅ Strong"| Interaction[Simulate full interaction:<br/>open → navigate → verify focus moved<br/>→ verify action fired exactly once]

  Meta --> FalseGreen[Can pass while bug persists<br/>in real user flow]
  Interaction --> TrueSignal[Fails only when real<br/>user path is broken]
```

### Rule: Test the user contract, not the implementation metadata

```dart
// ❌ WEAK — proves identifiers exist, not that interaction works
expect(find.bySemanticsLabel('workspace-row-0'), findsOneWidget);
expect(find.bySemanticsLabel('workspace-row-1'), findsOneWidget);

// ✅ STRONG — proves the actual navigation contract
await tester.sendKeyEvent(LogicalKeyboardKey.arrowDown);
await tester.pump();
// Verify: focus moved to next row
expect(focusedRow, equals(1));
// Verify: navigation fired exactly once
expect(switchCount, equals(1));
// Verify: previous row is no longer focusable via Tab
final prevRowSemantics = ...; // get semantics of row 0
expect(prevRowSemantics.isFocusable, isFalse);
```

## Anti-pattern #4 — Hard-coded English labels in DOM matching

**Problem**: Browser focus monitor code matches DOM nodes by visible text labels instead of stable semantic identifiers.

```mermaid
flowchart TD
  Match([Need to find DOM element]) --> How{Matching strategy}
  How -->|"❌ FRAGILE"| Text["querySelector('[aria-label=Settings]')<br/>Match by English label"]
  How -->|"✅ STABLE"| Ident["querySelector('[flt-semantics-identifier=X]')<br/>Match by semantic identifier"]

  Text --> Breaks[Breaks on:<br/>• locale change<br/>• label text update<br/>• dynamic content]
  Ident --> Stable[Stable across:<br/>• all locales<br/>• text changes<br/>• content updates]
```

### Rule: Always use `flt-semantics-identifier` for DOM matching

```dart
// ❌ WRONG — breaks on locale change
final el = document.querySelector('[aria-label="Settings"]');
final els = document.querySelectorAll('[aria-label*="Workspace switcher"]');

// ✅ CORRECT — stable identifiers set via Semantics(identifier: ...)
final el = document.querySelector('[flt-semantics-identifier="settings-button"]');
final els = document.querySelectorAll('[flt-semantics-identifier^="workspace-row-"]');
```

## Anti-pattern #5 — Roving tabindex not fully implemented

**Problem**: Setting `Semantics(focusable: true)` on all list items instead of only the active one, breaking the roving tabindex pattern.

```mermaid
flowchart TD
  Pattern([Roving tabindex pattern]) --> Active{Is this the<br/>active/selected item?}
  Active -->|Yes| Tab0["Semantics(focusable: true)<br/>→ tabindex='0' in DOM<br/>+ focused: true, selected: true"]
  Active -->|No| TabN1["Semantics(focusable: false)<br/>→ tabindex='-1' in DOM<br/>+ focused: false, selected: false"]

  Tab0 --> FocusNode["FocusNode(skipTraversal: false)"]
  TabN1 --> SkipNode["FocusNode(skipTraversal: true)"]

  FocusNode --> Sync[Call syncBrowserTabIndices()<br/>after state change]
  SkipNode --> Sync
```

### Rule: Conditional focusable based on active state + DOM sync

```dart
// In _WorkspaceSwitcherRowState:
Semantics(
  identifier: '${workspaceRowIdentifierPrefix}${widget.workspace.name}',
  focusable: widget.isActive,    // ← CONDITIONAL
  focused: widget.isActive,
  selected: widget.isActive,
  child: ...
)

// Focus node:
FocusNode(skipTraversal: !widget.isActive)

// After every selection change:
syncBrowserWorkspaceSwitcherRowTabIndices(); // DOM may lag behind Dart state
```

## Anti-pattern #6 — Browser focus workaround instead of root fix

**Problem**: Intercepting `Tab` key to manually move focus instead of fixing the actual focus export order.

```mermaid
flowchart TD
  Approach([Tab order wrong in browser]) --> Options{Fix approach}
  Options -->|"❌ WORKAROUND"| Intercept["Intercept Tab key in JS<br/>Manually call element.focus()<br/>on the 'correct' target"]
  Options -->|"✅ ROOT FIX"| FixExport["Fix Semantics sortKey/order<br/>Fix FocusTraversalOrder<br/>Verify DOM tabindex reflects state"]

  Intercept --> Problems["• Fragile: breaks if elements change<br/>• Partial: doesn't fix Shift+Tab<br/>• Browser-specific: no widget test coverage"]
  FixExport --> Robust["• Works on all platforms<br/>• Testable in widget tests<br/>• Browser inherits correct order"]
```

### Rule: Fix the source (Dart Semantics/Focus), not the symptom (DOM focus)

Only use browser-side focus manipulation (`element.focus()`, tabindex sync) as a **supplement** when Flutter web engine doesn't correctly export Dart state to DOM. Never as the primary fix.

## Checklist before submitting a keyboard/focus PR

```mermaid
flowchart TD
  A([Ready to submit?]) --> B{All previously-focusable<br/>elements still reachable?}
  B -->|No| FAIL1[❌ Restore removed focus targets]
  B -->|Yes| C{Single handler<br/>per key per context?}
  C -->|No| FAIL2[❌ Remove duplicate handler]
  C -->|Yes| D{DOM identifiers used<br/>instead of text labels?}
  D -->|No| FAIL3[❌ Use flt-semantics-identifier]
  D -->|Yes| E{Widget test exercises<br/>real interaction path?}
  E -->|No| FAIL4[❌ Add interaction test]
  E -->|Yes| F{Roving tabindex:<br/>only active item focusable?}
  F -->|N/A or Yes| G{Browser test confirms<br/>DOM matches Dart state?}
  F -->|No| FAIL5[❌ Set focusable conditionally]
  G -->|Not checked| FAIL6[❌ Verify with Playwright or local build]
  G -->|Yes| OK([✅ Submit PR])
```

## Flutter web focus layers — reference

```mermaid
graph TB
  subgraph Dart["Dart Layer (testable with flutter test)"]
    FTP[FocusTraversalPolicy<br/>OrderedTraversalPolicy]
    FTO[FocusTraversalOrder<br/>NumericFocusOrder]
    FN2[FocusNode<br/>skipTraversal]
    CS2[CallbackShortcuts<br/>KeyboardListener]
    SEM[Semantics<br/>focusable/focused/selected/identifier/sortKey]
  end

  subgraph Engine["Flutter Web Engine (not directly testable)"]
    SemTree[Semantics tree → DOM]
    TabCalc[tabindex calculation]
    FocusBridge[Focus event bridge]
  end

  subgraph DOM["Browser DOM (testable with Playwright)"]
    FLT[flt-semantics nodes]
    TABIDX[tabindex attributes]
    ARIA[aria-* attributes]
    DOMF[document.activeElement]
  end

  FTP --> SEM
  FTO --> SEM
  FN2 --> SEM
  SEM --> SemTree
  SemTree --> FLT
  TabCalc --> TABIDX
  FocusBridge --> DOMF

  style Dart fill:#e8f4fd,stroke:#1a73e8
  style Engine fill:#fff3e0,stroke:#e65100
  style DOM fill:#e8f5e9,stroke:#2e7d32
```

**Key gap**: The Engine layer sometimes doesn't update `tabindex` attributes after Dart `Semantics` changes. This is why `syncBrowserWorkspaceSwitcherRowTabIndices()` exists — it manually corrects DOM state when the engine lags.

## Summary of rules

| # | Rule | Triggered by |
|---|------|-------------|
| 1 | One key handler per context — never duplicate browser + Flutter handlers | PR #815 double ArrowDown |
| 2 | Never remove focus from visible interactive elements to fix order of others | PR #818 ExcludeFocus on theme toggle |
| 3 | Test the user interaction contract, not just semantics metadata | PR #815, #826 weak tests |
| 4 | Use `flt-semantics-identifier`, never English text labels, for DOM matching | PR #826 hard-coded labels |
| 5 | Roving tabindex: `focusable` must be conditional on active state | PR #827 (our fix for TS-870) |
| 6 | Fix focus order at the Dart Semantics source, not via Tab interception | PR #826 Tab interceptor |
| 7 | After any Semantics state change, call DOM sync for web platform | Engine lag gap |
| 8 | Widget test + Playwright test = complete coverage for keyboard bugs | Widget alone is insufficient |
