# Licensing

*What is open, what is not, and how the project stays MIT while standing on tools that are not.*

The project is open source from its first commit under the MIT licence (see `LICENSE`), like its
sibling projects. MIT covers everything in this repository unless a file says otherwise: the
engine, workers, faces (web UI, HTTP API, MCP server, CLI), the iPhone capture app, infrastructure
as code, documentation and tests.

## Why MIT

- **Consistent with the owner's other projects** (Chemigram, Orrery), and the most widely
  understood permissive licence.
- **Compatible with the default stack.** COLMAP and GLOMAP (BSD-3), gsplat and Brush (Apache-2.0),
  MapAnything's Apache checkpoint, SAM 2 (Apache-2.0), LightGlue (Apache-2.0 per its README),
  ALIKED (BSD-3), Open3D (MIT), Rerun (MIT or Apache-2.0), rawpy (MIT) over LibRaw (LGPL-2.1 or
  CDDL-1.0), mvs-texturing (BSD-3). MIT code may depend on all of these; their own licences keep
  applying to them. Sources: [tools overview](reference/tools-overview.md).
- **The alternative considered: Apache-2.0.** It adds an explicit patent grant and a NOTICE
  convention. It would matter if contributors' patents were a real concern; for a project started
  by one person and its agents, MIT's simplicity wins. Apache-licensed dependencies are used under
  their own terms either way, and their NOTICE files ship with any bundled copy.

## The boundary rules

MIT stays honest only if nothing more restrictive is pulled into the MIT code. Three rules:

1. **Copyleft tools run as separate processes, never as imports.** darktable (GPL, for the develop
   stage, possibly through Chemigram), OpenMVS and OpenSplat (AGPL), PyMeshLab (GPL-3.0): if used
   at all, they are optional plug-ins invoked as external programs, installed by the user,
   never vendored, never imported into the engine's Python process.
2. **Restricted model weights are never shipped.** Non-commercial or custom-licensed weights —
   VGGT-1B, Pi3/Pi3X, MASt3R/DUSt3R, MapAnything's CC-BY-NC checkpoint, SAM 3, SuperPoint — are
   optional plug-ins the user downloads under the weights' own terms. Each plug-in states its
   licence in the stage registry, and every reconstruction's provenance records the licence of
   every implementation that touched it.
3. **No dataset lives in the repository.** Public datasets are fetched by scripts, under their own
   licences, into a local cache outside git. Most of the useful ones are non-commercial
   ([public datasets](reference/public-datasets.md)): fine for development and research results,
   not for redistribution. The benchmark code is MIT; the benchmark data is whatever its source
   allows.

## What is not in this repository

| Not here | Where it lives |
|---|---|
| Photos and captures (the owner's, friends', robots') | Local storage; never committed |
| Public datasets | Local cache, fetched by script |
| Restricted model weights | Downloaded by the user per plug-in |
| Secrets (tailnet keys, cloud credentials) | Never committed; see the infrastructure docs when they exist |

## Open points

- The licence of Refractive COLMAP (the main underwater candidate) is unknown; it is adopted only
  once known, under rule 1 or as a dependency if permissive.
- Test fixtures with real photos need their own licence per file (Chemigram uses CC BY-SA 4.0 for
  its raw fixtures); decided when the first fixture is added.
