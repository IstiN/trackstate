---
name: dmtools-configure-parent-context
description: Configure automatic parent story and sibling subtask context fetching for DMTools AI agents. Use when setting up or modifying agent input enrichment, adding BA/SA/VD sibling context, or configuring Jira custom fields for parent context retrieval.
metadata:
  model: models/gemini-3.1-pro-preview
  last_modified: Thu, 11 Jun 2026 10:30:00 GMT
---
# Configuring Parent Context Fetch for DMTools Agents

## Contents
- [When to Use This Skill](#when-to-use-this-skill)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Agent Setup](#agent-setup)
- [Integration Test](#integration-test)
- [Troubleshooting](#troubleshooting)

## When to Use This Skill

Use this skill when you need to:

1. Add parent story context (`parent-KEY.md`) to agent input folders
2. Add sibling BA/SA/VD subtask context (`parent_context_ba.md`, `parent_context_sa.md`, `parent_context_vd.md`)
3. Configure Jira custom fields (Acceptance Criteria, Solution, Diagrams, etc.) for context retrieval
4. Set up a new project with parent context enrichment
5. Debug missing parent context files in agent input

## How It Works

The `fetchParentContextToInput.js` pre-CLI action:

1. Reads the current ticket's **parent key** from `ticket.fields.parent`
2. Fetches the **parent story** with configured fields → writes `input/parent-{KEY}.md`
3. Runs a **JQL search** for siblings with `[BA]`, `[SA]`, or `[VD]` prefix → writes `input/parent_context_{ba,sa,vd}.md`
4. All fields are rendered as clean markdown with human-readable labels

### File Layout in Input Folder

```
input/
└── TICKET/
    ├── request.md
    ├── comments.md
    ├── parent-TS-100.md           ← parent story (configurable fields)
    ├── parent_context_ba.md       ← Business Analysis sibling
    ├── parent_context_sa.md       ← Solution Architecture sibling
    └── parent_context_vd.md       ← Visual Design sibling
```

## Configuration

### 1. Project Config (`.dmtools/config.js`)

Add `jira.parentContextFetch` to enable globally:

```js
module.exports = {
  jira: {
    project: 'TS',
    parentTicket: 'TS-1',
    parentContextFetch: {
      enabled: true,
      resolveFieldNames: true,     // resolves "Acceptance Criteria" → "customfield_10397"
      parentFields: [              // fields for parent-KEY.md
        'key',
        'summary',
        'description',
        'status',
        'Acceptance Criteria',
        'Solution',
        'Diagrams'
      ],
      siblingFields: [             // fields for parent_context_*.md
        'key',
        'summary',
        'description',
        'status',
        'comment',
        'Acceptance Criteria'
      ]
    }
  },
  defaultTracker: 'jira'
};
```

**Field names:** Use human-readable names (e.g. `"Acceptance Criteria"`). DMTools resolves them to `customfield_*` IDs automatically when `resolveFieldNames: true`.

**Project-specific fields:** Find your custom field names via:

```bash
curl -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "https://YOUR-JIRA.atlassian.net/rest/api/3/issue/KEY?expand=names"
```

### 2. Agent JSON Override

For per-agent customization, add `customParams.parentContextFetch`:

```json
{
  "params": {
    "customParams": {
      "parentContextFetch": {
        "enabled": true,
        "parentFields": ["key", "summary", "description", "status", "Acceptance Criteria"],
        "siblingFields": ["key", "summary", "description", "status", "comment"]
      }
    }
  }
}
```

### 3. Agent Prompts

Ensure the agent reads parent context files. Add `input_context_reading.md` to `cliPrompts`:

```json
{
  "cliPrompts": [
    "./agents/instructions/common/input_context_reading.md"
  ]
}
```

The `input_context_reading.md` mermaid diagram instructs the agent to read:
- `input/TICKET/parent-KEY.md` — parent story summary, description, ACs
- `input/TICKET/parent_context_ba.md` / `sa.md` / `vd.md` — BA/SA/VD context

## Agent Setup

### Enable for an Agent

Add `preCliJSAction` to the agent JSON:

```json
{
  "params": {
    "preCliJSAction": "agents/js/fetchParentContextToInput.js"
  }
}
```

**Agents that should use it:**
- `solution_description.json` — needs parent ACs and Solution field
- `po_refinement.json` — needs parent context for product decisions
- `story_questions.json` — via `fetchQuestionsToInput.js` (auto-chained)
- `story_development.json` — via `preCliDevelopmentSetup.js` (auto-chained)
- `bug_development.json` — via `preCliDevelopmentSetup.js` (auto-chained)
- `pr_review.json` — via `preparePRForReview.js` (auto-chained)
- `pr_rework.json` — via `preCliReworkSetup.js` (auto-chained)

### Composite Script Chaining

If the agent already has a composite pre-CLI script, chain `fetchParentContextToInput.js` at the end:

```js
// In preCliDevelopmentSetup.js or similar
var fetchParentContext = require('../fetchParentContextToInput.js');
fetchParentContext.action(params);
```

## Integration Test

Run the dmtools jsrunner integration test against a real ticket:

```bash
cd agents

# Subtask with parent story
dmtools run js/integration-tests/run_fetchParentContext_test.json

# Story with parent epic
dmtools run js/integration-tests/run_fetchParentContext_TS575.json

# Subtask with [SA] sibling
dmtools run js/integration-tests/run_fetchParentContext_JD9.json

# Story with filled custom fields (Acceptance Criteria, Solution, Diagrams)
dmtools run js/integration-tests/run_fetchParentContext_TS728.json
```

Check `outputs/input/parent-*.md` for generated content.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No files generated | `parentContextFetch.enabled !== true` | Enable in `.dmtools/config.js` or agent `customParams` |
| Only `parent-*.md`, no siblings | No `[BA]`/`[SA]`/`[VD]` subtasks under parent | Normal — create BA/SA/VD subtasks |
| Custom fields missing | Fields empty in Jira or wrong field name | Verify field names via Jira API `?expand=names` |
| `file_write` not called | `jira_get_ticket` returns empty fields | Check Jira permissions and API token |
| Sibling search fails | JQL syntax error | Check Jira v2 vs v3 API compatibility |
| Agent ignores parent context | `input_context_reading.md` not in cliPrompts | Add it to agent JSON cliPrompts |

### Debug with Real API

```bash
# Check what dmtools returns for a ticket
cat > /tmp/debug.json << 'EOF'
{
  "name": "JSRunner",
  "params": {
    "jsPath": "js/unit-tests/debug.js"
  }
}
EOF

cat > agents/js/unit-tests/debug.js << 'EOF'
function action() {
  var ticket = jira_get_ticket({ key: 'TS-637', fields: ['summary', 'customfield_10397'] });
  console.log('Keys: ' + Object.keys(ticket.fields).join(', '));
  return {};
}
EOF

dmtools run /tmp/debug.json
```
