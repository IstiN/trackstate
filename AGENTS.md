## CodeGraph

CodeGraph builds a semantic knowledge graph of codebases for faster, smarter code exploration.

### If `.codegraph/` exists in the project

**Answer directly with CodeGraph — don't delegate exploration to a file-reading sub-agent or a grep/read loop.** CodeGraph *is* the pre-built search index; re-deriving its answers with grep + Read repeats work it already did and costs more for the same result. For "how does X work?", architecture, trace, or where-is-X questions, answer in a handful of CodeGraph calls and stop — typically with **zero file reads**. The returned source is complete and authoritative: treat it as already read and do not re-open those files. Reach for raw Read/Grep only to confirm a specific detail CodeGraph didn't cover.

**Tool selection by intent:**

| Tool | Use For |
|------|---------|
| `codegraph_context` | Map a task / feature / area first — composes search + node + callers + callees in one call |
| `codegraph_trace` | "How does X reach Y" — the call path, each hop's body inline (follows dynamic-dispatch hops grep can't) |
| `codegraph_explore` | Survey several related symbols' source in ONE budget-capped call |
| `codegraph_search` | Find a symbol by name |
| `codegraph_callers` / `codegraph_callees` | Walk call flow one hop at a time |
| `codegraph_impact` | Check what's affected before editing |
| `codegraph_node` | Get a single symbol's source / signature |

A direct CodeGraph answer is a handful of calls; a grep/read exploration is dozens.

### If `.codegraph/` does NOT exist

At the start of a session, ask the user if they'd like to initialize CodeGraph:

"I notice this project doesn't have CodeGraph initialized. Would you like me to run `codegraph init -i` to build a code knowledge graph?"

---

## 📦 Repomix Code Snapshots

Use **repomix** to generate a full-repo overview or targeted code snapshots for investigation, onboarding, or feeding context to an LLM.

- **Install** (one-time): `npm install -g repomix`
- **Full project snapshot**:
  ```bash
  repomix .
  ```
  Output: `snapshots/repomix-output.xml`
- **Specific files** (e.g., after a grep/codegraph search):
  ```bash
  echo 'src/some_file.dart' | repomix --stdin --compress --output snapshots/target.xml
  ```
- **Multiple files**:
  ```bash
  printf 'lib/a.dart\nlib/b.dart\n' | repomix --stdin --compress --output snapshots/target.xml
  ```

> **Tips**:
> - `--compress` uses Tree-sitter to keep signatures and replace method bodies with `⋮----`, significantly reducing token count.
> - Always use `--stdin` for specific file lists — multiple `--include` flags are unreliable.
> - `snapshots/` is `.gitignore`d — never commit generated XML files.
