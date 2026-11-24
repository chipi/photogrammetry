# AGENTS.md: photogrammetry

Canonical, tool-agnostic instructions for any coding agent working in this repository. `CLAUDE.md` points here. This file layers on top of the owner's global agent rules, which live outside the repository and are loaded by the agent's own tooling; it never contradicts them.

## What this project is

An open-source reconstruction engine that turns photographs into 3D models (camera poses, point clouds, meshes, gaussian splats) and reports what it knows and what it does not: scale, frame, coverage and uncertainty. Read [README.md](README.md) and [docs/concept/PG-brief.md](docs/concept/PG-brief.md) first. The project is in its concept phase; prototypes and code start next. "photogrammetry" is a working name.

## Repository layout

| Path | Holds |
|---|---|
| `docs/concept/` | Concept package PG-00..PG-05, narrative docs |
| `docs/reference/` | Standing reference: primer, tools, datasets, product analysis |
| `docs/wip/` | Dated research, reviews and drafts; may be superseded |
| `docs/LICENSING.md` | The licensing boundary rules |
| `src/recon/` | The engine package (`recon`) |
| `tests/` | Tests for `src/recon` |
| `prototypes/PG-P<n>-<slug>/` | Step 0 prototypes, one folder each |
| `mockups/PG-M<n>-<slug>/` | Step 0 UX mock-ups, one folder each ([plan](docs/wip/visual-ideas.md)) |
| `scripts/` | Repo tooling, such as `check_docs.sh` |
| `apps/ios/`, `infra/` | Later; not created yet |

## Doc system

- The concept package PG-00..PG-05 is narrative prose in `docs/concept/`.
- Formal artifacts come later: `docs/prd`, `docs/rfc`, `docs/adr`, `docs/uxs`, with reference docs PA, IA and TA.
- Each PRD has a "Why this is a PRD" sentence.
- Each RFC has "Why this is an RFC", "Alternatives considered" and "Closing evidence".
- ADRs are append-only and short; a changed decision is a new ADR that supersedes the old one. Each has a Status (Accepted or Superseded) and "Alternatives considered".
- Each UXS has a "Visual fidelity" field and a "Boundary note".
- When code and a doc disagree, one is wrong; find which and fix it.

## Voice rules

Present tense, declarative, specific. Do not write "the user shall", "in order to", "it is worth noting" or "at this point in time". No emoji. `scripts/check_docs.sh` checks the banned phrases.

## Commit convention

Every commit that changes a doc has a "Cross-doc check:" section in its body, listing the dependent docs checked.

## Branching

No pull requests: the project has one contributor. Work lands on `main` directly, after `make check`
passes locally and the commit is rebased on `origin/main`; CI runs on every push to `main` and is
watched until it settles. A red CI run on `main` is fixed before anything else lands. Short-lived
local branches are fine; nothing waits on review. Force-pushing and deleting `main` are blocked.

## Licensing boundary

Summary of [docs/LICENSING.md](docs/LICENSING.md); the file is authoritative.

- The repository is MIT.
- Copyleft tools (GPL, AGPL) run only as external processes, never imported or vendored.
- Restricted model weights are never shipped; they are optional plug-ins the user downloads.
- No dataset or capture is ever committed.

## Data rules

Datasets and captures live in a local cache outside git. The path comes from the environment variable `PG_DATA_DIR`, default `~/.cache/photogrammetry`. `.gitignore` blocks the common data and RAW extensions, and `make docs-check` fails if git tracks any.

## Python rules

- Tooling: `uv`, src layout, package `recon`. The CLI will be `recon`.
- Lint and format with `ruff`; test with `pytest`.
- Engine code (`src/recon`) requires tests.
- Prototypes may be scrappier, but each has a README with its "proven when" criterion and its result.
- Dependencies are added deliberately and only with the owner's approval.

## Make targets

| Target | Does |
|---|---|
| `make help` | Lists targets (default) |
| `make setup` | `uv sync --all-groups` |
| `make lint` | `ruff check` and `ruff format --check` |
| `make format` | Applies ruff formatting and safe fixes |
| `make test` | `pytest` |
| `make docs` | `mkdocs build --strict` into `site/` |
| `make docs-serve` | Live-reload docs at `http://127.0.0.1:8000` |
| `make docs-check` | `scripts/check_docs.sh`: links, voice, per-artifact rules, private-guide leak, tracked data |
| `make check` | lint + test + docs + docs-check; ends with `CHECK: PASS` or `CHECK: FAIL` |
| `make clean` | Removes caches and build output |

Run `make check` before proposing a commit. CI (`.github/workflows/ci.yml`, job `ci`) runs the same steps. A new doc must appear in the `nav` of `mkdocs.yml`; the site name lives only in `mkdocs.yml`.

## Secrets

Never commit secrets: `.env` files, keys, tokens. Only `.env.example` with placeholders is tracked.
