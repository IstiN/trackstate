# Bug Development — Critical Anti-Patterns

These patterns caused 6–13 review rework cycles. Read and avoid them.

## 1. Widget test passes ≠ browser works

```mermaid
flowchart TD
  Fix([Implement fix]) --> WT{Widget test\npasses?}
  WT -->|Yes| BT{Does the ticket\nfail in BROWSER\n(Playwright/Chromium)?}
  BT -->|Not tested| WRONG["❌ NEVER assume widget = browser\nFlutter web semantics differ from native focus"]
  BT -->|Still fails| Root["Root cause is in browser layer:\n- Semantics tree export order\n- tabindex synchronization\n- JS interop bridge"]
  BT -->|Passes| OK([✅ Ship])
  WT -->|No| Fix2[Fix the Dart code first]
```

**Rule**: If the ticket mentions browser tab order, focus, or Playwright — a passing widget test alone is NOT sufficient. The browser semantics tree is a separate system.

## 2. Never use DOM-wide workarounds for focus order bugs

```mermaid
flowchart TD
  Problem([Focus order wrong\nin browser]) --> A{Fix approach?}
  A -->|"Intercept Tab/Arrow\nin JS and reroute"| BAD["❌ BLOCKING\nThis is a workaround, not a fix.\nReviewer WILL reject."]
  A -->|"Fix the exported\nsemantics sort order"| GOOD["✅ Fix the Flutter semantics\ntree sort keys so browser\nnaturally tabs correctly"]
  BAD --> Real[Investigate:\n1. OrdinalSortKey values\n2. Semantics child order\n3. FocusTraversalGroup scope]
```

**Rule**: Browser focus order comes from the semantics tree export. Fix the source, not the symptom.

## 3. No full-DOM scans on keyboard events

```mermaid
flowchart TD
  Key([Keyboard event fires]) --> Scan{Need to find\nscroll target?}
  Scan -->|"querySelectorAll('*')\n+ getBoundingClientRect"| BAD["❌ BLOCKING\nO(n) DOM walk on every keypress\n= performance regression"]
  Scan -->|"Cache on panel open\nreuse on keypress"| GOOD["✅ Compute once, reuse"]
```

**Rule**: Expensive DOM queries (querySelectorAll, getComputedStyle, getBoundingClientRect) must be cached. Never run per-keypress.

## 4. Mixed-scroll: identify the ACTUAL scroller

When both `window` and a Flutter semantics scroller exist:
- Don't default to `window` — check which element has the relevant `scrollTop`
- Capture BOTH, restore only whichever drifted
- The Flutter semantics scroller often owns the actual content scroll

## 5. Test must prove the TICKET scenario, not a subset

If the ticket says "ArrowDown should advance selection AND not scroll background":
- ❌ Testing only "ArrowDown is classified as prevent-default" — too weak
- ✅ Testing actual scroll position before/after AND selection change

## 6. Read the previous failed PR before starting

```
git log --oneline --all -- 'lib/ui/features/tracker/services/browser_workspace*' | head -10
```

Check what was already tried. Don't repeat the same approach the reviewer already rejected.

## 7. NEVER write bug-fix tests under `testing/`

```mermaid
flowchart TD
  Fix([Bug fix TDD]) --> Loc{Where is the
failing test?}
  Loc -->|testing/tests/...| BAD["❌ BLOCKING\n`testing/` is owned by test-automation agents.\nMove the test to `test/` (Flutter/Dart unit/widget)."]
  Loc -->|test/| GOOD([✅ Correct unit-test tree])
```

**Rule**: Bug development TDD tests belong in the project's standard unit-test tree (`test/` for Flutter/Dart). Regression / workflow-observation / accessibility tests under `testing/` are updated only by test-automation agents.

## 8. NEVER add unrelated changes to a bug fix PR

```mermaid
flowchart TD
  Fix([Bug fix ready]) --> Scope{Does the diff\ntouch files OUTSIDE\nthe bug's scope?}
  Scope -->|"Locale UI, new keys,\nother product areas"| BAD["❌ BLOCKING\nReviewer WILL reject.\nSplit into separate PR."]
  Scope -->|Only files needed\nfor the fix| OK([✅ Ship])
```

**Rule**: If the ticket is about accessibility-gate logging, do NOT also refactor locale settings UI. One ticket = one concern. Unrelated changes get instant BLOCKING rejection.

## 9. Assertions must be specific, not regex-broad

```python
# ❌ WRONG — matches ANY message with generic words
assert re.search(r'match|directory|repository|path|workspace', message)

# ✅ CORRECT — matches the SPECIFIC error from the ticket
assert 'workspace directory mismatch' in message or \
       'selected directory does not contain' in message
```

**Rule**: Generic word-matching passes on unrelated failures. Use exact expected error variants from the ticket description.

## 10. Test seed state must match ticket precondition EXACTLY

If the ticket says "workspace is Local Unavailable":
- ❌ Seeding a healthy hosted workspace (test passes without exercising the fail path)
- ✅ Seeding the exact broken state described in preconditions

```mermaid
flowchart TD
  Ticket["Ticket precondition:\n'broken local workspace'"] --> Seed{What does\ntest seed?}
  Seed -->|Healthy hosted workspace| BAD["❌ BLOCKING\nTest never exercises\nthe ticket scenario"]
  Seed -->|Exact broken state| GOOD["✅ Test exercises\nthe real failure path"]
```
