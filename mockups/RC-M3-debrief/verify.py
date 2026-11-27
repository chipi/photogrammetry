"""RC-M3: check the agent's debrief against the tools it claims to quote, and stamp readiness.

Every handle is replayed: the tool is called again with the same arguments and the field read
from its result. A claim is `supported` when every handle matches and every number in its text
is one of its handles' values (or a number in a handle's field or arguments, such as the 2 in
`at_2cm`); `unsupported` when a handle fails or a number has no handle; `judgement` when it has
no number and no handle. The readiness stamps are rules, not the agent's opinion: each states
its requirement and is computed from the same tools.

    uv run --directory prototypes/RC-P3-quality python ../../mockups/RC-M3-debrief/verify.py <data>
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P3-quality"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tools

RUN = "courtyard/full"
# Region ids, photo names and section numbers are names, not quantities.
NAMES = re.compile(r"\bR\d{3}\b|DSC_\d+(?:\.JPG)?|dslr_images/\S+")
NUMBER = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?")


def call(tool: str, args: dict, data: Path):
    if tool == "get_products":
        return json.loads((data / "products.json").read_text())
    if tool in ("list_cameras", "suggest_shots", "get_engine_debrief"):
        import debrief_server

        return getattr(debrief_server, tool)(**args)
    if tool == "list_annotations":
        return json.loads((data / "annotations.json").read_text())
    if tool in ("get_summary", "list_regions", "get_region"):
        return getattr(tools, tool)(**args)
    raise ValueError(f"no such read tool {tool!r}")


def walk(doc, path: str):
    for key in [k for k in str(path).split(".") if k]:
        if key == "#":
            doc = len(doc)
        elif isinstance(doc, list):
            doc = doc[int(key)]
        else:
            doc = doc[key]
    return doc


def numbers_in(value) -> list[float]:
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, int | float):
        return [float(value)]
    if isinstance(value, list):
        return [x for v in value for x in numbers_in(v)]
    if isinstance(value, dict):
        return [x for v in value.values() for x in numbers_in(v)]
    return [float(m) for m in re.findall(r"\d+(?:\.\d+)?", str(value))]


def close(claimed: str, actual: float) -> bool:
    """The claimed text is the actual value rounded to the claim's own precision, as a share
    or as a percentage."""
    c = float(claimed.replace(",", ""))
    places = len(claimed.split(".")[1]) if "." in claimed else 0
    half = 0.5 * 10**-places + 1e-9
    return any(abs(c - v) <= half or abs(c - v) <= 0.005 * abs(v) for v in (actual, actual * 100))


def check_claim(claim: dict, data: Path) -> dict:
    results, known = [], []
    for h in claim.get("handles", []):
        try:
            got = walk(call(h["tool"], h.get("args", {}), data), h["field"])
            ok = any(close(str(x), got) for x in numbers_in(h["value"])) or got == h["value"]
            if isinstance(got, list | dict):
                ok = got == h["value"]
            results.append({**h, "actual": got, "ok": bool(ok)})
            known += numbers_in(got)
        except (KeyError, IndexError, ValueError, TypeError) as e:
            results.append({**h, "actual": None, "ok": False, "error": str(e)})
        known += numbers_in(h["field"]) + numbers_in(h.get("args", {}))
    text = NAMES.sub(" ", claim["text"])
    loose = [n for n in NUMBER.findall(text) if not any(close(n, k) for k in known)]
    if not results and not loose:
        status = "judgement"
    elif all(r["ok"] for r in results) and not loose:
        status = "supported"
    else:
        status = "unsupported"
    return {**claim, "handles": results, "unbacked_numbers": loose, "status": status}


def readiness(data: Path) -> list[dict]:
    s = tools.get_summary(RUN)
    p = call("get_products", {}, data)
    scale = s["scale"]["state"]
    reg = s["registration"]
    v = p["viewer"]

    def ev(tool, field, args=None):
        args = {"run": RUN} if args is None and tool != "get_products" else (args or {})
        return {
            "tool": tool,
            "args": args,
            "field": field,
            "value": walk(call(tool, args, data), field),
        }

    web = v["iphone_15_pro_fps"] >= 30 and v["m4_pro_chrome_fps"] >= 59.5
    return [
        {
            "use": "Web viewing",
            "status": "pass" if web else "fail",
            "requires": "mesh and splat in one browser page at 30 fps or more on a phone and at "
            "a 60 Hz display's ceiling on a laptop (RC-P6's criterion)",
            "because": f"{v['iphone_15_pro_fps']} fps on an iPhone 15 Pro, "
            f"{v['m4_pro_chrome_fps']} fps on an M4 Pro",
            "evidence": [
                ev("get_products", "viewer.iphone_15_pro_fps"),
                ev("get_products", "viewer.m4_pro_chrome_fps"),
            ],
        },
        {
            "use": "Measurement",
            "status": "fail" if scale == "arbitrary" else "unknown",
            "requires": "a known scale (markers, priors or a scale bar), then 90% of the surface "
            "within 2 cm",
            "because": f"scale is {scale}: {s['scale']['reason']}. Against the laser scan, "
            f"{p['mesh']['at_2cm']['accuracy']:.0%} of the mesh is within 2 cm",
            "evidence": [
                ev("get_summary", "scale.state"),
                ev("get_products", "mesh.at_2cm.accuracy"),
            ],
        },
        {
            "use": "Robot localisation",
            "status": "fail" if scale == "arbitrary" else "unknown",
            "requires": "metric scale, every photo registered in one component",
            "because": f"{reg['registered']} of {reg['images']} photos in {reg['components']} "
            f"component; scale {scale}",
            "evidence": [
                ev("get_summary", "registration.rate"),
                ev("get_summary", "registration.components"),
                ev("get_summary", "scale.state"),
            ],
        },
        {
            "use": "Print",
            "status": "unknown",
            "requires": "a closed (watertight) mesh at known scale",
            "because": p["mesh"]["closed_note"],
            "evidence": [ev("get_products", "mesh.closed_note")],
        },
    ]


def final_json(text: str) -> dict:
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if blocks:
        return json.loads(blocks[-1])
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


def main():
    data = Path(sys.argv[1])
    raw = json.loads((data / "agent_raw.json").read_text())
    doc = final_json(raw["result"])
    sections = [
        {**sec, "claims": [check_claim(c, data) for c in sec["claims"]]} for sec in doc["sections"]
    ]
    claims = [c for sec in sections for c in sec["claims"]]
    count = {
        k: sum(c["status"] == k for c in claims) for k in ("supported", "unsupported", "judgement")
    }
    out = {
        "title": doc.get("title", "Debrief"),
        "agent": {
            k: raw.get(k) for k in ("num_turns", "duration_ms", "total_cost_usd", "session_id")
        },
        "sections": sections,
        "count": count,
        "readiness": readiness(data),
        "annotations": json.loads((data / "annotations.json").read_text())
        if (data / "annotations.json").is_file()
        else [],
    }
    (data / "debrief.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(count), f"{len(out['annotations'])} annotations")
    for c in claims:
        if c["status"] != "supported":
            print(f"  {c['status']}: {c['text'][:100]} | unbacked {c['unbacked_numbers']}")


if __name__ == "__main__":
    main()
