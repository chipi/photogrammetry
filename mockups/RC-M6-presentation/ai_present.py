"""RC-M6: the optional AI layer. One model call looks at the photo behind each stop of the tour
and drafts a title, a two-sentence introduction and a caption per stop. What a caption says is in
a photo is the model's reading (a judgement); every number it uses cites a fact below, and this
script checks it. Writes data/ai.json; without it the page uses the captions its rule writes.

    python3 ai_present.py data [model]        (runs `claude -p`; default model sonnet)
    python3 ai_present.py data --recheck      (re-checks the recorded answer, no call)

The call runs with no MCP servers, no settings sources and its own system prompt: the default
context of `claude -p` is what a person's own AI would not carry.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

NUMBER = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?")
NAMES = re.compile(r"DSC_\d+(?:\.JPG|\.jpg)?|\b[23]D\b")  # photo names and "3D" are not numbers

SYSTEM = "You write short, plain captions for a 3D model shown to people outside the field."

PROMPT = """You are the optional AI layer of a 3D reconstruction tool; the person connected you
and the tool works without you. The person is making a presentation of a model of a courtyard:
a guided camera path that stops at some of the photos the model was built from. Read each stop's
photo with the Read tool (the paths are below), then write:

- "title": at most six words.
- "intro": two sentences for a viewer who knows nothing about photogrammetry: what they are
  looking at and how it was made.
- "stops": one caption per stop, at most fourteen words, saying what the viewer sees there.
  Describe only what is in that photo; do not guess what the place is used for or where it is.

Every number in any text must be cited: its key in the facts and its value. End with one JSON
object and nothing after it:
{"title": {"text": "...", "cites": []}, "intro": {"text": "...", "cites": [{"path":
"photos", "value": 38}]}, "stops": [{"photo": "DSC_0295", "text": "...", "cites": []}]}

Facts:
"""


def facts(meta: dict) -> dict:
    res = meta["camera_centre_residual_m"]
    return {
        "photos": len(meta["cameras"]),
        "stops": len(meta["stops"]),
        "walk_m": meta["walk_m"],
        "mesh_faces": meta["mesh_faces"],
        "splat_gaussians": meta["splat_gaussians"],
        "scale_residual_median_m": round(res["median"], 2),
        "scale_residual_median_cm": round(res["median"] * 100),
    }


def close(text: str, value: float) -> bool:
    c = float(text.replace(",", ""))
    places = len(text.split(".")[1]) if "." in text else 0
    half = 0.5 * 10**-places + 1e-9
    return any(abs(c - v) <= half or abs(c - v) <= 0.005 * abs(v) for v in (value, value * 100))


def check(claim: dict, fx: dict) -> dict:
    known = []
    for cite in claim.get("cites", []):
        v = fx.get(cite.get("path"))
        cite["actual"] = v
        cite["ok"] = isinstance(v, int | float) and close(str(cite["value"]), v)
        if isinstance(v, int | float):
            known.append(float(v))
    numbers = NUMBER.findall(NAMES.sub(" ", claim["text"]))
    loose = [n for n in numbers if not any(close(n, k) for k in known)]
    claim["unbacked"] = loose
    if loose or not all(c["ok"] for c in claim.get("cites", [])):
        claim["status"] = "unsupported"
    else:
        claim["status"] = "supported" if claim.get("cites") else "judgement"
    return claim


def main() -> None:
    data = Path(sys.argv[1]).resolve()
    model = sys.argv[2] if len(sys.argv) > 2 else "sonnet"
    meta = json.loads((data / "meta.json").read_text())
    fx = facts(meta)
    if model == "--recheck":
        out = json.loads((data / "ai.json").read_text())
        for c in [out["title"], out["intro"], *out["stops"]]:
            check(c, fx)
            print(c["status"].ljust(11), c["unbacked"], c["text"])
        (data / "ai.json").write_text(json.dumps(out, indent=1))
        return
    stops = [meta["cameras"][i]["name"] for i in meta["stops"]]
    paths = "\n".join(f"Stop {k + 1}: {data / 'photos' / f'{n}.jpg'}" for k, n in enumerate(stops))
    run = subprocess.run(  # noqa: S603 (an argument list, no shell; the prompt is ours)
        [
            shutil.which("claude") or "claude",
            "-p",
            PROMPT + json.dumps(fx, indent=1) + "\n\nStops:\n" + paths,
            "--model",
            model,
            "--output-format",
            "json",
            "--tools",
            "Read",
            "--allowedTools",
            "Read",
            "--add-dir",
            str(data / "photos"),
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--system-prompt",
            SYSTEM,
            "--max-budget-usd",
            "0.50",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=True,
    )
    raw = json.loads(run.stdout)
    text = raw["result"]
    doc = json.loads(text[text.index("{") : text.rindex("}") + 1])
    out = {
        "model": f"Claude {model.capitalize()}",
        "cost_usd": raw.get("total_cost_usd"),
        "input_tokens": raw.get("usage", {}).get("input_tokens"),
        "title": check(doc["title"], fx),
        "intro": check(doc["intro"], fx),
        "stops": [check(s, fx) | {"photo": s.get("photo")} for s in doc["stops"]],
        "facts": fx,
    }
    for c in [out["title"], out["intro"], *out["stops"]]:
        print(c["status"].ljust(11), c["unbacked"], c["text"])
    (data / "ai.json").write_text(json.dumps(out, indent=1))
    print("cost", out["cost_usd"])


if __name__ == "__main__":
    main()
