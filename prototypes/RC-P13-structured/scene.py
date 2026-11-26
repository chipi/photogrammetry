"""The tool-neutral structured description that every RC-P13 segment writes and every tool reads.

A scene is JSON: a frame, the inputs it came from, a list of elements and a list of
measurements. Each element and measurement states its source:

- measured: fitted to the reconstruction; carries evidence and an uncertainty with its basis;
- inferred: closed by a rule or a model (a wall's thickness, an unseen corner);
- unknown: inside the structure but not observed; drawn as a hole, never filled in.

Pure standard library, so Blender's own Python can import it.
"""

import json
from pathlib import Path

SCHEMA = "recce-structured/0.1"
SOURCES = ("measured", "inferred", "unknown")


def element(id, kind, source, geometry, sigma_m=None, sigma_basis=None, evidence=None, **attrs):
    return {
        "id": id,
        "kind": kind,
        "source": source,
        "geometry": geometry,
        "sigma_m": sigma_m,
        "sigma_basis": sigma_basis,
        "evidence": evidence,
        "attributes": attrs,
    }


def measurement(
    id, of, value_m, source, sigma_m=None, sigma_basis=None, bias_m=None, evidence=None
):
    return {
        "id": id,
        "of": of,
        "value_m": value_m,
        "source": source,
        "sigma_m": sigma_m,
        "bias_m": bias_m,
        "sigma_basis": sigma_basis,
        "evidence": evidence,
    }


def scene(segment, frame, inputs, elements, measurements, notes=()):
    return {
        "schema": SCHEMA,
        "segment": segment,
        "frame": frame,
        "inputs": inputs,
        "elements": elements,
        "measurements": measurements,
        "notes": list(notes),
    }


def validate(s):
    """Problems with a scene, as strings; empty when it keeps the rules."""
    problems = []
    if s.get("schema") != SCHEMA:
        problems.append(f"schema is {s.get('schema')!r}, not {SCHEMA!r}")
    ids = [e["id"] for e in s["elements"]] + [m["id"] for m in s["measurements"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        problems.append(f"duplicate ids: {sorted(dupes)}")
    known = set(ids)
    for x in s["elements"] + s["measurements"]:
        problems += source_problems(x)
    problems += [
        f"{m['id']}: refers to missing element {ref}"
        for m in s["measurements"]
        for ref in m["of"]
        if ref not in known
    ]
    return problems


def source_problems(x):
    """What an element or measurement owes for the source it claims."""
    where, source = x["id"], x["source"]
    if source not in SOURCES:
        return [f"{where}: source {source!r} is not one of {SOURCES}"]
    out = []
    if source == "measured" and not x.get("evidence"):
        out.append(f"{where}: measured without evidence")
    if source == "measured" and (x.get("sigma_m") is None or not x.get("sigma_basis")):
        out.append(f"{where}: measured without an uncertainty and its basis")
    if source == "unknown" and x.get("sigma_m") is not None:
        out.append(f"{where}: unknown cannot carry an uncertainty")
    return out


def write(s, path):
    problems = validate(s)
    if problems:
        raise ValueError("scene breaks the rules:\n  " + "\n  ".join(problems))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(s, indent=1))


def read(path):
    s = json.loads(Path(path).read_text())
    problems = validate(s)
    if problems:
        raise ValueError(f"{path} breaks the rules:\n  " + "\n  ".join(problems))
    return s
