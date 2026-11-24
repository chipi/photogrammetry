# CLAUDE.md: photogrammetry

The canonical agent-instruction file for this repo is **[AGENTS.md](AGENTS.md)**. It is tool-agnostic and applies to every coding agent. Everything below adds Claude-specific notes and does not replace it.

@AGENTS.md

---

## Reading order for any non-trivial task

1. **AGENTS.md**: layout, doc system, voice, data and Python rules, make targets.
2. **[docs/concept/PG-brief.md](docs/concept/PG-brief.md)**: what the project is, what is settled, the prototype plan.
3. **[docs/concept/PG-architecture-sketch.md](docs/concept/PG-architecture-sketch.md)**: the logical architecture.
4. The relevant doc in `docs/reference/` (primer, tools, datasets, product analysis) for your task area.

If a doc and the code disagree, one is wrong; fix it.

## Gate

Run `make check` and trust its `CHECK: PASS` / `CHECK: FAIL` line and exit code before proposing a commit.
