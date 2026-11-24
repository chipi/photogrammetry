# photogrammetry

*Working name.* An open-source reconstruction engine that turns photographs into 3D models —
camera poses, point clouds, meshes and gaussian splats — and always says what it knows and what it
does not: scale, frame, coverage and uncertainty.

It is built for three kinds of client at once: a person with a phone, a GoPro or a DSLR; robots
that hand over capture sets with known poses; and AI agents that read the engine's quality state
and decide what to capture next. Its flagship domain is underwater — large sets of high-resolution
RAW photos of wrecks and reefs — processed across all the machines its owner has, with rented GPUs
joining when a job outgrows them.

## Status

Concept phase. There is no code yet. The project is being shaped through a concept package and a
set of prototypes that test its riskiest assumptions first.

## Read first

| Document | What it holds |
|---|---|
| [Brief](docs/concept/PG-brief.md) | Where the project comes from, what it is, what is settled, the prototype plan |
| [Architecture sketch](docs/concept/PG-architecture-sketch.md) | The logical architecture: faces, engine, workers, the reconstruction model, configurability, distribution |
| [Use cases](docs/concept/PG-use-cases.md) | The first captures walked through the architecture as a thought experiment |
| [Photogrammetry primer](docs/reference/photogrammetry-primer.md) | The theory behind every stage |
| [Tools overview](docs/reference/tools-overview.md) | Libraries, models, formats and products, with licences and platform support |
| [Product feature analysis](docs/reference/product-feature-analysis.md) | What Metashape and others offer; MVP tiers |
| [Public datasets](docs/reference/public-datasets.md) | Datasets for development, with ground truth and licences |
| [Licensing](docs/LICENSING.md) | MIT, and the rules that keep it honest |

Working notes and research live in [`docs/wip/`](docs/wip/).

## Layout

```text
docs/concept/     concept package (PG-NN documents) and its working sketches
docs/reference/   standing reference: theory, tools, products, datasets
docs/wip/         research notes, reviews, working notes
```

The engine, workers, web UI, iPhone app (`apps/ios/`) and infrastructure code arrive in this same
repository as the prototypes begin.

## Licence

[MIT](LICENSE). Optional plug-ins, model weights and datasets keep their own licences; see
[Licensing](docs/LICENSING.md).
