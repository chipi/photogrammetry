"""RC-P3: the three read tools an agent uses to find a weak region. Plain functions returning
JSON-able dicts; `mcp_server.py` wraps them one to one.

A run is a folder holding quality.json; `run` is a path, or an id relative to the runs root
(`RECCE_P3_RUNS`, default ~/.cache/recce/runs/p3), for example `kicker/heldout`.
"""

import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("RECCE_P3_RUNS", "~/.cache/recce/runs/p3")).expanduser()


def _load(run: str) -> dict:
    path = Path(run).expanduser()
    if not path.is_absolute():
        path = ROOT / run
    qfile = path / "quality.json" if path.is_dir() else path
    if not qfile.is_file():
        raise ValueError(f"no quality.json for run {run!r} under {ROOT}")
    return json.loads(qfile.read_text())


def _weakest_first(doc: dict) -> list[dict]:
    return sorted(doc["regions"], key=lambda r: (r["coverage"], r["id"]))


def get_summary(run: str) -> dict:
    """Overall state of a reconstruction: registration, reprojection, scale, the images that did
    not register and why, and a count of regions with a flag. Start here, then call list_regions."""
    doc = _load(run)
    bad = [i for i in doc["images"] if i["verdict"] != "registered"]
    regions = doc["regions"]
    return {
        "schema": doc["schema"],
        "run": run,
        "scale": doc["scale"],
        "registration": doc["registration"],
        "reprojection": doc["reprojection"],
        "images_not_registered": [
            {"name": i["name"], "verdict": i["verdict"], "reason": i["reason"]} for i in bad
        ],
        "regions": {
            "total": len(regions),
            "flagged": sum(bool(r["flags"]) for r in regions),
            "no_points": sum("no_points" in r["flags"] for r in regions),
            "coverage_median": sorted(r["coverage"] for r in regions)[len(regions) // 2],
        },
    }


def list_regions(run: str, limit: int | None = None) -> dict:
    """Every region of the scene, weakest coverage first. coverage is 0..1: the share of the
    360 degree view ring around the region that has a camera, scaled down when the region holds
    fewer points than in the reference run. centre is the middle of the region's grid cell in the
    scene frame. flags name the gap kinds: no_points, thin_angle, few_photos."""
    doc = _load(run)
    rows = [
        {
            "id": r["id"],
            "centre": r["cell_centre"],
            "coverage": r["coverage"],
            "points": r["points"],
            "reference_points": r["reference_points"],
            "images_seeing": len(r["images_seeing"]),
            "flags": r["flags"],
        }
        for r in _weakest_first(doc)
    ]
    return {
        "run": run,
        "frame": doc["frame"]["id"] if doc["frame"] else None,
        "regions": rows[:limit] if limit else rows,
        "total": len(rows),
    }


def get_region(run: str, region_id: str) -> dict:
    """All metrics of one region and the images that see it: point count, supporting images,
    median triangulation angle, few-photo fraction, azimuth coverage and its largest empty arc."""
    doc = _load(run)
    region = next((r for r in doc["regions"] if r["id"] == region_id), None)
    if region is None:
        raise ValueError(f"unknown region {region_id!r}; ids: {[r['id'] for r in doc['regions']]}")
    verdict = {i["name"]: i["verdict"] for i in doc["images"]}
    return {
        "run": run,
        **region,
        "images_seeing": [{"name": n, "verdict": verdict.get(n)} for n in region["images_seeing"]],
        "scale": doc["scale"]["state"],
    }
