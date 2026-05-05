---
version: alpha
name: TrackState.AI
description: >
  Git-native Jira-compatible project tracker. Premium warm aesthetic,
  dual-theme, no blue. Visual references in vs_references/.
colors:
  # Primary — Terracotta scale (brand accent)
  primary-600: "#CD5B3B"
  primary-500: "#D2694A"
  primary-400: "#E8A085"
  primary-300: "#DE6E4F"
  primary-200: "#F2D2C4"
  primary: "#CD5B3B"
  # Secondary — Olive scale
  secondary-600: "#6D7F4F"
  secondary-500: "#7E9B5F"
  secondary-400: "#8CB85A"
  secondary-300: "#9CD648"
  secondary-200: "#E7EED8"
  secondary: "#6D7F4F"
  # Accent — Amber scale
  accent-600: "#D9A21B"
  accent-500: "#F2B538"
  accent-400: "#F7C966"
  accent-300: "#FEDF9D"
  accent-200: "#FFF1CF"
  accent: "#D9A21B"
  # Neutral scale (dark to light)
  neutral-100: "#2D2A26"
  neutral-200: "#3A3835"
  neutral-300: "#454540"
  neutral-400: "#6B6D63"
  neutral-500: "#8A8A80"
  neutral-600: "#B5A498"
  neutral-700: "#E5D3B8"
  neutral-800: "#F1E4D5"
  neutral-900: "#FAF8F4"
  neutral: "#FAF8F4"
  # Semantic
  success: "#3BBE60"
  warning: "#C1B341"
  error: "#C25742"
  info: "#5A5F18"
  # Surface (light theme)
  surface: "#FFFFFF"
  on-surface: "#2D2A26"
  # Surface (dark theme)
  surface-dark: "#3A3835"
  on-surface-dark: "#FAF8F4"
typography:
  display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.3
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: 0.03em
  caption:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0.02em
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.5
rounded:
  none: 0px
  xs: 2px
  sm: 4px
  md: 8px
  lg: 12px
  xl: 16px
  full: 9999px
spacing:
  0: 0px
  1: 4px
  2: 8px
  3: 12px
  4: 16px
  5: 20px
  6: 24px
  7: 28px
  8: 32px
  9: 36px
  10: 40px
  11: 44px
  12: 48px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-900}"
    rounded: "{rounded.md}"
    padding: 12px
  button-primary-hover:
    backgroundColor: "{colors.primary-400}"
    textColor: "{colors.neutral-100}"
  button-primary-active:
    backgroundColor: "{colors.primary-600}"
  button-primary-disabled:
    backgroundColor: "{colors.neutral-400}"
    textColor: "{colors.neutral-600}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.neutral-900}"
    rounded: "{rounded.md}"
    padding: 12px
  button-secondary-hover:
    backgroundColor: "{colors.neutral-300}"
  button-secondary-disabled:
    backgroundColor: "transparent"
    textColor: "{colors.neutral-500}"
  input-field:
    backgroundColor: "{colors.neutral-200}"
    textColor: "{colors.neutral-900}"
    rounded: "{rounded.md}"
    padding: "{spacing.3}"
  input-field-hover:
    backgroundColor: "{colors.neutral-300}"
  input-field-active:
    backgroundColor: "{colors.neutral-200}"
  input-field-disabled:
    backgroundColor: "{colors.neutral-200}"
    textColor: "{colors.neutral-500}"
  card:
    backgroundColor: "{colors.neutral-200}"
    textColor: "{colors.neutral-900}"
    rounded: "{rounded.lg}"
    padding: "{spacing.6}"
  tag-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-900}"
    rounded: "{rounded.full}"
    padding: "{spacing.1}"
  tag-default:
    backgroundColor: "{colors.neutral-300}"
    textColor: "{colors.neutral-700}"
    rounded: "{rounded.full}"
    padding: "{spacing.1}"
---

# TrackState.AI

## Overview

TrackState.AI is a Git-native, Jira-compatible project tracker built with Flutter. The visual identity conveys premium craftsmanship and warm professionalism — a modern productivity tool that feels fresh, elegant, and delightful without corporate coldness.

The design uses three chromatic scales — Primary (Terracotta), Secondary (Olive), Accent (Amber) — over warm neutrals. Two first-class themes — light and dark — share the same component structure, spacing, and accent palette with contrast-adjusted surfaces. Both themes must be fully functional, covered by golden tests, and switchable at runtime.

**Visual references** (approved POC mockups and styleguide in `vs_references/`):

| File | Purpose |
|------|---------|
| `vs_references/white_theme.png` | Light theme — primary UI reference for default experience |
| `vs_references/dark_theme.png` | Dark theme — alternative theme for low-light / developer preference |
| `vs_references/icons_promo.png` | Icon set and promotional visual identity |
| `vs_references/styleguide_references.png` | Full styleguide — color scales, typography, spacing, radius, component tokens, icon set, do's/don'ts |

Developers and agents must consult these images when implementing or reviewing any UI component. Golden tests must visually match the established design direction.

## Colors

The palette uses three chromatic scales — Primary (Terracotta), Secondary (Olive), Accent (Amber) — plus a full neutral ramp and four semantic colors. No blue as primary or accent. No neon. No Claude Code palette. No cyberpunk gradients.

The styleguide (`vs_references/styleguide_references.png`) defines the dark theme token values. For the light theme, surfaces and backgrounds invert: `neutral-900` becomes the page background, `neutral-100` becomes primary text, and card surfaces use `#FFFFFF` instead of `neutral-200`.

### Primary — Terracotta (brand accent)

- **P-600 (#CD5B3B):** Core terracotta — primary actions, key highlights, the most important interactive element per screen.
- **P-500 (#D2694A):** Slightly lighter — secondary emphasis.
- **P-400 (#E8A085):** Warm mid-tone — hover states, accent containers.
- **P-300 (#DE6E4F):** Bright terracotta — active/pressed states.
- **P-200 (#F2D2C4):** Pale peach — light theme accent backgrounds, subtle containers.

### Secondary — Olive

- **S-600 (#6D7F4F):** Core olive — success states, completed indicators, positive feedback.
- **S-500 (#7E9B5F):** Mid olive.
- **S-400 (#8CB85A):** Bright olive — progress bars, active success states.
- **S-300 (#9CD648):** Light olive.
- **S-200 (#E7EED8):** Pale olive — success container backgrounds.

### Accent — Amber

- **A-600 (#D9A21B):** Core amber — warning states, in-progress indicators, attention.
- **A-500 (#F2B538):** Mid amber.
- **A-400 (#F7C966):** Light amber — hover/container.
- **A-300 (#FEDF9D):** Pale amber — warning container backgrounds.
- **A-200 (#FFF1CF):** Near-white amber — subtle warm highlights.

### Neutral scale

- **N-100 (#2D2A26):** "Warm Charcoal" — darkest neutral. Dark theme primary text, light theme headlines.
- **N-200 (#3A3835):** Dark theme card/surface backgrounds.
- **N-300 (#454540):** Dark theme elevated containers, hover states.
- **N-400 (#6B6D63):** Muted — disabled states, inactive borders.
- **N-500 (#8A8A80):** Mid gray — secondary text in dark theme.
- **N-600 (#B5A498):** Warm sand — borders, dividers, inactive chips.
- **N-700 (#E5D3B8):** Warm parchment.
- **N-800 (#F1E4D5):** Light warm — sidebar background in light theme, subtle containers.
- **N-900 (#FAF8F4):** "Ivory" — lightest neutral, light theme page background. Never pure white.

### Semantic colors

- **Success (#3BBE60):** Positive outcomes, done states, passing checks.
- **Warning (#C1B341):** Attention needed, in-progress, pending review.
- **Error (#C25742):** Failures, blockers, overdue, destructive actions.
- **Info (#5A5F18):** Informational badges, neutral notifications.

## Typography

The typography strategy uses **Inter** for all UI text and **JetBrains Mono** for code, JQL queries, issue keys, and technical identifiers. Both are open-source, cross-platform, and render cleanly in Flutter on all targets.

- **Display (48px/700):** Hero headlines, onboarding screens, splash text. Tight letter spacing (-0.02em).
- **Headline LG (32px/700):** Screen titles, dashboard section headers. -0.02em spacing.
- **Headline MD (24px/600):** Issue summaries in detail view, dialog titles. -0.01em spacing.
- **Headline SM (20px/600):** Card headings, section subheaders. -0.01em spacing.
- **Body LG (16px/400):** Long-form descriptions, comments. Line height 1.6 for readability.
- **Body MD (14px/400):** Default body text, metadata values. Line height 1.5.
- **Body SM (12px/400):** Secondary metadata, timestamps, helper text. 0.01em spacing.
- **Label LG (14px/600):** Field names, navigation items, prominent tags.
- **Label MD (12px/500):** Compact field labels, chip text, table headers. 0.02em spacing.
- **Label SM (11px/500):** Micro-labels, badge text, footnotes. 0.03em spacing.
- **Caption (10px/400):** Smallest text — version stamps, fine print. 0.02em spacing.
- **Code MD (JetBrains Mono 13px/400):** JQL queries, issue keys (`TRACK-123`), code blocks, and technical identifiers.

## Layout

The layout follows a sidebar + content model for desktop and a single-column model for mobile:

- **Desktop:** Fixed-width left sidebar (240–280px) with project navigation and quick filters. Remaining width is fluid content area with a maximum comfortable reading width (1200px) for issue detail.
- **Mobile:** Single-column stack with bottom navigation bar. Sidebar collapses to drawer.
- **Spacing scale:** 8px base grid with 4px half-step. 13 levels: 0 (0px) through 12 (48px). Components grouped using containment cards with generous internal padding (level 6 = 24px) for approachability.
- **Grid:** Content areas use a responsive grid. Board columns are flexible-width. List views use full-width rows.

## Elevation & Depth

Depth is achieved through **Tonal Layers** and subtle warm shadows rather than heavy drop shadows:

- **Light theme:** Cards sit on the ivory background with a soft warm shadow (`0 1px 3px rgba(45, 42, 38, 0.08)`). Elevated modals and dropdowns use slightly stronger shadow.
- **Dark theme:** Cards use a lighter surface color against the deep background. A faint warm glow replaces shadow for elevated surfaces.
- Avoid harsh black shadows. All shadow colors should be warm-tinted (based on the primary color, not pure black).

## Shapes

The shape language uses **Consistent Rounded Corners** across all interactive elements:

- Cards and containers: `lg` (12px) radius for a soft, modern feel
- Buttons, inputs, and chips: `md` (8px) radius
- Status badges and pills: `full` (9999px) for fully rounded
- Icons and avatars: circular (`full` radius)
- No mixing of sharp and rounded corners within the same view

## Components

### Buttons
- **Primary:** Terracotta background (`primary`), ivory text (`neutral-900`), `md` rounded. Used for the single most important action per screen. Hover → `primary-400`, Active → `primary-600`, Disabled → `neutral-400` bg / `neutral-600` text.
- **Secondary:** Transparent background, text color `neutral-900`, `md` rounded. Hover → `neutral-300` bg. Disabled → `neutral-500` text.
- **Destructive:** Error background (`error`), ivory text. Always requires confirmation dialog.
- **Ghost:** No border, subtle text. Used in toolbars and compact action areas.

### Cards and surfaces
- Rounded `lg` (12px) corners, consistent across all cards.
- Dark theme: `neutral-200` background. Light theme: `#FFFFFF` background.
- Subtle warm shadow for depth without heavy drop shadows.
- Internal padding: spacing level 6 (24px).
- Clean internal spacing with clear content zones separated by light dividers.

### Issue cards (board and list views)
- Issue key prominently displayed in monospace (`code-md` typography).
- Priority indicator: color dot or icon, left-aligned.
- Summary text with truncation for board cards, full display in list view.
- Assignee avatar, status badge (pill chip), and label chips.
- Subtle hover/focus state using `neutral-300` (dark) or `neutral-800` (light) background.

### Status badges
- Rounded pill shape (`full` radius) with status-specific container color.
- Compact `label-sm` text, clear contrast against container.
- Active/selected tags: `primary` bg / `neutral-900` text.
- Default/inactive tags: `neutral-300` bg / `neutral-700` text.

### Navigation
- Left sidebar with project selector, navigation sections, quick filters. Background: `neutral-800` (light) or `neutral-100` (dark).
- Top bar with JQL search input, user profile avatar, theme toggle, language selector.
- Breadcrumb trail for issue hierarchy context (Epic → Story → Sub-task).

### Input fields
- Background: `neutral-200` (dark) / `surface` (light). Rounded `md`.
- Hover → `neutral-300`. Active → retain bg with `primary` focus ring.
- Disabled → `neutral-200` bg / `neutral-500` text.
- Internal padding: spacing level 3 (12px).
- Inline validation with `error` color and clear messaging.
- Markdown editor for descriptions with preview toggle.

### Icons

> **IMPORTANT:** All icons must be custom SVG, written from scratch. No icon font libraries (Material Icons, FontAwesome, etc.). Each icon must be hand-designed to match the warm, rounded aesthetic of the design system.

- Consistent icon set matching `vs_references/icons_promo.png` and `vs_references/styleguide_references.png`.
- Outlined style for navigation and metadata icons. Filled style for active states.
- Stroke width: consistent 1.5–2px across all icons.
- Git-native visual cues: branch, commit, merge, sync status, webhook, repository indicator.
- Issue type icons: Epic (lightning/bolt), Story (bookmark), Sub-task (nested checkbox).
- Utility icons: Attachment, Link, Settings, User, Live.
- All icons must be accessible as Flutter `Widget` via a centralized `TrackStateIcons` class.
- Export SVG source alongside the Flutter widget for design reference.

### Screens

- **Project dashboard:** Status distribution summary cards, active epics with progress indicators, recent activity feed, quick-action buttons.
- **Issue board (Kanban):** Column headers with status name and issue count, draggable cards, swimlane support, collapsible columns.
- **JQL search / issue list:** Query bar with syntax highlighting, sortable column headers, dense readable rows, pagination, saved filter management.
- **Issue detail:** Full-width layout with metadata sidebar, inline editable fields, comment thread with markdown rendering, attachment gallery, linked issues, hierarchy breadcrumb, workflow transition button bar, Git activity timeline.
- **Hierarchy tree:** Indented tree view with expand/collapse, Git-folder-inspired metaphor, issue type icons at each level, status and assignee inline.
- **Settings / configuration:** Tabbed interface for issue types, statuses, workflows, fields, priorities, versions, components. Language/locale selector, theme toggle preview, project metadata editor.
- **Mobile adaptation:** Single-column responsive layout, bottom navigation, swipe gestures for status transitions, compact touch-optimized issue cards, collapsible metadata on issue detail.

## Do's and Don'ts

- Do use the terracotta accent (`primary`) only for the single most important action per screen
- Do maintain WCAG AA contrast ratios (4.5:1 for normal text, 3:1 for large text)
- Do keep both light and dark themes visually consistent in structure and spacing
- Do use monospace font (JetBrains Mono) for all issue keys, JQL queries, and code content
- Do consult `vs_references/` images before implementing or reviewing any UI component
- Do write golden tests for every UI asset, screen, and reusable component
- Do keep all UI data mockable with fixtures/fakes — no live dependencies in visual tests
- Do design all custom SVG icons from scratch — hand-draw each to match the warm rounded aesthetic
- Do use the exact token values from the YAML frontmatter — never approximate colors or spacing
- Do adapt dark theme tokens for light theme by inverting neutral scale roles
- Don't use blue as a primary or accent color
- Don't use pure white (`#FFFFFF`) as a page background or pure black (`#000000`) as a dark theme background
- Don't mix rounded and sharp corners in the same view
- Don't use more than two font weights on a single screen section
- Don't use neon colors, cyberpunk gradients, or Claude Code-inspired palettes
- Don't use icon font libraries (Material Icons, FontAwesome, etc.) — all icons must be custom SVG
- Don't invent a new visual style for screens not yet covered — extrapolate from the existing design language

## Agent Usage

This design reference must be consulted by agents during:

- **PO refinement and story writing:** Acceptance criteria for UI stories should reference specific screens, components, and tokens from this document and the `vs_references/` images.
- **Development:** Flutter implementation must match the visual direction and token values. Golden tests must verify adherence.
- **Test automation:** UI test cases must validate visual consistency against this design language, token values, and reference images.
- **PR review:** Reviewers should flag UI changes that deviate from these guidelines without documented justification.

When generating new screens or components not explicitly covered here, extrapolate from the established design language, token values, and reference images. Do not invent a new visual style.
