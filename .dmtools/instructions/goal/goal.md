# TrackState.AI Goal

## Product vision

TrackState.AI is a Git-native, Jira-compatible tracking system intended to replace Jira for software delivery teams while keeping the workflows, query language, and JSON shapes that automation already expects.

The system must support the main Jira capabilities used by dm.ai agents and MCP tools, expose a CLI that returns Jira-compatible JSON, and provide a Flutter application that can run locally, on the web, and on mobile while storing all tracker state in Git-compatible artifacts.

## Non-negotiable requirements

- **Jira replacement scope**: TrackState.AI is designed as a full Jira replacement from day one, not just a limited dm.ai helper.
- **JQL compatibility**: Search must support Jira-compatible JQL syntax and semantics for the supported issue model.
- **Git as source of truth**: Tracker data, configuration, workflows, and artifacts must be represented through Git-compatible files and commands.
- **Demo template repository**: There must be a separate GitHub template repository that users can fork to get a working demo project with all required prerequisites and sample data.
- **GitHub Pages deployment**: The Flutter app must compile as a single-page application and run from GitHub Pages after users fork the repository and enable Pages.
- **GitHub repository authorization**: Prefer a no-GitHub-App authorization path based on the signed-in user's GitHub permissions and repository collaborator access. A GitHub App may be introduced only if browser/mobile constraints make direct OAuth/PAT-based access insufficient.
- **Replaceable SCM provider**: GitHub is the first supported hosted provider, but all GitHub-specific APIs, authorization, Pages deployment, collaborator checks, pull requests, and file operations must be wrapped behind provider interfaces that can be replaced with GitLab, Azure DevOps, or another Git host later.
- **Multi-runtime data access**: The Flutter app should use direct Git commands when running locally, and GitHub APIs when running in web or mobile environments.
- **CLI JSON compatibility**: The CLI must return JSON shaped like Jira responses used by dm.ai's Jira MCP tools.
- **Multi-language support**: The product must support localization from the beginning, including translated UI labels, configurable project/field/status names, locale-aware formatting, and a clean path for community-provided language packs.
- **Accessibility**: The product must be usable by people with disabilities. All interactive elements must have meaningful Semantics labels for screen readers, the UI must support keyboard/focus navigation, maintain WCAG AA color contrast ratios, and provide logical focus order across all screens and runtimes.
- **Binary artifacts**: Attachments and large binary artifacts must use Git LFS. Markdown, JSON, and small metadata files may remain regular Git files.

## Jira MCP parity target

TrackState.AI must cover these Jira MCP methods from `dm.ai/dmtools-ai-docs/references/mcp-tools/jira-tools.md`:

| Area | Required methods |
|---|---|
| Ticket lifecycle | `jira_create_ticket_basic`, `jira_create_ticket_with_json`, `jira_create_ticket_with_parent`, `jira_delete_ticket`, `jira_get_ticket`, `jira_update_ticket`, `jira_update_description`, `jira_update_field`, `jira_update_all_fields_with_name`, `jira_clear_field`, `jira_update_ticket_parent` |
| Search and JQL | `jira_search_by_jql`, `jira_search_by_page`, `jira_search_with_pagination` |
| Workflow/status | `jira_get_project_statuses`, `jira_get_transitions`, `jira_move_to_status`, `jira_move_to_status_with_resolution` |
| Metadata | `jira_get_fields`, `jira_get_all_fields_with_name`, `jira_get_field_custom_code`, `jira_get_issue_types`, `jira_get_components`, `jira_get_fix_versions`, `jira_get_issue_link_types` |
| Users/auth profile | `jira_get_my_profile`, `jira_get_user_profile`, `jira_get_account_by_email`, `jira_assign_ticket_to` |
| Labels, versions, priority | `jira_add_label`, `jira_remove_label`, `jira_set_fix_version`, `jira_add_fix_version`, `jira_remove_fix_version`, `jira_set_priority` |
| Comments | `jira_get_comments`, `jira_post_comment`, `jira_post_comment_if_not_exists` |
| Hierarchy and links | `jira_get_subtasks`, `jira_link_issues` |
| Attachments | `jira_attach_file_to_ticket`, `jira_download_attachment` |
| Compatibility escape hatch | `jira_execute_request` |

## Candidate storage model

The issue storage format is not final yet. Treat this as a candidate architecture to evaluate and refine:

```text
PROJECT/
  project.json
  config/
    fields.json
    statuses.json
    issue-types.json
    workflows.json
    priorities.json
    components.json
    versions.json
  PROJECT-123/
    main.md
    acceptance_criteria.md
    comments/
      0001.md
      0002.md
    attachments/
      screenshot.png
    links.md
```

A nested tree layout is a strong candidate for the default human-facing structure because it makes hierarchy visible in the filesystem and can reduce the need to open files just to understand parent-child relationships:

```text
PROJECT/
  PROJECT-1/
    main.md                 # Epic
    PROJECT-2/
      main.md               # Story or Task
      PROJECT-3/
        main.md             # Sub-task
```

This is allowed and should be evaluated as the preferred layout if it does not break Jira-compatible lookup, stable issue keys, re-parenting, or Git merge behavior. The implementation must still be able to resolve an issue by key regardless of its path, because issue keys are stable while hierarchy may change. If a ticket is moved from one parent to another, the move should be represented by a Git rename/move plus metadata update rather than creating a new issue.

`links.md` should not be required for hierarchy when the directory tree and issue metadata already express parent/child relationships. Reserve `links.md` or an equivalent structured links file for non-hierarchical Jira relationships such as "blocks", "is blocked by", "relates to", "duplicates", and "clones".

Configuration should use JSON because it is machine-readable, schema-friendly, easy to validate, and maps cleanly to Jira-style REST/CLI responses. Markdown should be reserved for human-authored issue content such as descriptions, acceptance criteria, comments, and design notes.

`main.md` should use an Obsidian-compatible frontmatter/attribute style for structured fields, followed by human-readable summary and description content. The frontmatter is the canonical issue metadata for Git diffs, while JSON indexes may be generated from it for search/performance. Example:

```markdown
---
key: PROJECT-123
project: PROJECT
issueType: Story
status: Backlog
priority: Medium
assignee: github-user
reporter: github-user
labels:
  - ai-ready
components:
  - tracker-core
fixVersions: []
parent: null
created: 2026-05-05T00:00:00Z
updated: 2026-05-05T00:00:00Z
---

# Summary

Short issue summary.

# Description

Detailed issue description.
```

Alternative layouts may be proposed only if they improve Git merge behavior, JQL indexing, GitHub Pages performance, or Jira JSON compatibility.

Git commit history should be the canonical audit history for issue changes. Do not introduce a required per-issue `history.md` as source-of-truth because it duplicates Git history and creates extra merge conflicts. If UI/API performance requires a history view, generate it from Git commits and diffs, or store a clearly marked derived index such as `.trackstate/index/history.json` that can be rebuilt.

## Hierarchy example

TrackState.AI must support Jira-style hierarchy. A nested tree is the preferred candidate when it remains practical for Git operations:

```text
TRACK/
  project.json
  config/
    fields.json
    issue-types.json
    statuses.json
    workflows.json
  TRACK-1/
    main.md                 # Epic: Build TrackState.AI MVP
    TRACK-2/
      main.md               # Story: Implement JQL parser
      acceptance_criteria.md
      links.md              # Non-hierarchy relationships only
      TRACK-3/
        main.md             # Sub-task: Parse ORDER BY clause
      TRACK-4/
        main.md             # Sub-task: Implement pagination tokens
```

Epic issue metadata:

```markdown
---
key: TRACK-1
project: TRACK
issueType: Epic
status: In Progress
summary: Build TrackState.AI MVP
parent: null
epic: null
---
```

Story issue metadata linked to the Epic:

```markdown
---
key: TRACK-2
project: TRACK
issueType: Story
status: Backlog
summary: Implement JQL parser
parent: null
epic: TRACK-1
---
```

For a nested tree layout, `epic: TRACK-1` must match the ancestor Epic directory. Keeping it in metadata allows fast JQL evaluation and safe fallback if a generated index is stale.

Sub-task issue metadata linked to the Story:

```markdown
---
key: TRACK-3
project: TRACK
issueType: Sub-task
status: To Do
summary: Parse ORDER BY clause
parent: TRACK-2
epic: TRACK-1
---
```

For a nested tree layout, `parent: TRACK-2` must match the immediate parent issue directory. The canonical relationship can be validated by comparing metadata with the filesystem path.

JQL must be able to query these relationships, for example:

```sql
project = TRACK AND issueType = Story AND epic = TRACK-1
parent = TRACK-2 AND issueType in (Sub-task, Subtask, "Sub Task")
```

## Functional capability expectations

TrackState.AI should support:

- projects, issue keys, issue types, fields, custom fields, statuses, workflows, transitions, resolutions, priorities, labels, components, versions, assignees, reporters, watchers, comments, attachments, links, parent-child hierarchy, subtasks, audit history, and deleted/archived states;
- Jira-compatible field naming and custom field lookup by display name;
- JQL filtering, ordering, pagination, field projection, and parent/subtask queries;
- comments with enough Jira-markup compatibility for dm.ai generated comments;
- attachment upload/download backed by Git LFS;
- deterministic JSON output compatible with dm.ai MCP expectations;
- Git-friendly concurrency and conflict handling when multiple collaborators update issues;
- multi-language UI and metadata display, including locale-aware dates, numbers, sorting, pluralization, text direction readiness, and fallback behavior when translations are missing;
- local-first operation using Git commands and hosted operation through replaceable provider adapters, with GitHub as the initial adapter.

## Multi-language support

TrackState.AI must be designed for international teams from the start:

- all Flutter UI strings must be externalized through the app localization layer, not hard-coded in widgets;
- project admins should be able to configure display names for issue types, statuses, fields, priorities, resolutions, components, and workflow transitions per locale where practical;
- stored canonical values should remain stable machine identifiers, while localized labels are presentation metadata;
- CLI JSON responses should remain deterministic and Jira-compatible by default, with optional localized display fields when requested;
- JQL should query canonical field names and values reliably, while aliases/localized display names may be supported as an enhancement;
- date, time, number, and relative-time formatting must respect the user's locale;
- right-to-left language readiness should be considered in layout and component choices even if initial languages are left-to-right;
- language packs should be Git-backed and reviewable, for example under `config/i18n/*.json` or a similar schema-friendly location;
- missing translations must fall back explicitly to the default language without corrupting issue data.

## Application architecture expectations

The Flutter app must:

- compile to a web SPA suitable for GitHub Pages;
- support local desktop/developer use with direct Git commands;
- support web/mobile use through a hosted Git provider adapter, initially backed by GitHub APIs;
- read/write the same repository-backed tracker data model in all runtimes;
- avoid requiring a backend server for the default fork-and-run experience;
- provide issue list, detail, creation/editing, JQL search, comments, attachments, workflow transitions, and project configuration screens;
- include golden tests for all UI assets, reusable components, generated visual designs, and key screens;
- keep screen/widget data fully mockable with fixtures or fakes so visual tests do not require live Git, hosted provider APIs, Jira, network, or filesystem state;
- require developers to inspect generated UI images/design assets before accepting them and reject outputs that do not look polished, coherent, and aligned with TrackState.AI visual direction;
- provide full accessibility support: every interactive widget must have a meaningful Semantics label, screens must support screen readers, keyboard/focus navigation, sufficient color contrast (WCAG AA), and logical focus order;
- use Semantics labels as the canonical element identifiers for both accessibility and automated testing — widgets without proper labels are considered incomplete.

The CLI must:

- provide TrackState-native commands and Jira-compatible command aliases where useful;
- return JSON compatible with dm.ai Jira MCP usage;
- support local repository paths and hosted repository targets through provider adapters;
- use only Git-compatible operations for persistent state changes;
- fail explicitly on unsupported Jira behavior rather than returning misleading success.

Provider-specific code must stay behind explicit interfaces such as repository file storage, authentication/session, collaborator/permission lookup, Pages/static hosting deployment, pull request/review integration, branch/commit operations, and attachment/LFS operations. Product logic, JQL parsing, issue serialization, workflow transitions, and CLI JSON mapping must not depend directly on GitHub SDK/API types.

## Agent guidance

When implementing or refining TrackState.AI:

- use this goal file together with the existing TrackState scope, product-domain, development-focus, review-focus, rework-focus, and test-case instructions;
- do not narrow the product to a simple markdown issue tracker if that would prevent Jira-compatible behavior;
- preserve the Git-native model and keep GitHub Pages as the first deployment path without hard-coding GitHub as the only possible provider;
- treat JQL and CLI JSON compatibility as core product requirements;
- prefer designs that can be tested from a forked demo template repository without private infrastructure;
- explicitly document any deviation from Jira behavior and whether it is temporary, intentional, or deferred.
