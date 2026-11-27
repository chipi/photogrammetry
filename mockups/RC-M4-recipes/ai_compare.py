"""RC-M4: the optional AI layer. One model call reads the comparison of the two recipes (the
same numbers the page shows) and says which recipe suits which purpose; each number it uses
cites its path in that comparison, and this script checks every number against the path it
cites. Writes data/ai.json; without it the page shows only the rule-based verdict.

The call runs with no MCP servers, no settings sources and its own system prompt: the default
context of `claude -p` (its system prompt, instructions, every connected MCP server's tools)
is what a person's own AI would not carry.

    python3 ai_compare.py data [model]        (runs `claude -p`; default model sonnet)
    python3 ai_compare.py data --recheck      (re-checks the recorded answer, no call)
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

NUMBER = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?")
NAMES = re.compile(r"DSC_\d+(?:\.JPG)?|\b\d+th(?=[- ]percentile)")  # names, percentile labels

SYSTEM = "You explain 3D reconstruction results in plain words."
USAGE = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")

PROMPT = """You are the optional AI layer of a 3D reconstruction tool; the person connected you
and the tool works without you. Two recipes registered the same photos from the same matches:
COLMAP incremental and GLOMAP global. The comparison below has, per scene and recipe, the
quality numbers and the measured cost (seconds and energy above idle on one machine).

For each scene, write three or four short sentences in plain words for a person who does not
know photogrammetry: which recipe to use for web viewing, for measurement and for robot
localisation, and why; and one thing worth trying next. The ground-truth columns
(camera_off_truth_*) are known only for this benchmark; say so if you use them.

Every number in a sentence must be cited: its dot path in the comparison and its value. Write a
share as it appears, or times 100 with a percent sign. End with one JSON object and nothing
after it:
{"scenes": {"kicker": [{"text": "...", "cites": [{"path": "kicker.glomap_global.mapping_s",
"value": 6.9}]}], "courtyard": [...]}}

Comparison:
"""


def comparison(meta):
    out = {}
    for scene, m in meta["scenes"].items():
        out[scene] = {"images": m["images"]}
        for name, r in m["results"]["strategies"].items():
            pe = r["pose_error"]
            c = m["cost"]["stages"][name]
            out[scene][name] = {
                "registered": r["registered"],
                "points": r["points3D"],
                "reprojection_mean_px": round(r["reprojection_error_mean_px"], 2),
                "reprojection_p95_px": round(r["reprojection_error_p95_px"], 2),
                "camera_off_truth_median_pct": round(pe["position_frac_of_extent_median"] * 100, 2),
                "camera_off_truth_worst_pct": round(pe["position_frac_of_extent_max"] * 100, 2),
                "mapping_s": round(c["seconds"], 1),
                "mapping_mwh_above_idle": round(c["above_baseline_wh"] * 1000),
            }
    return out


def walk(doc, path):
    for k in path.split("."):
        doc = doc[k]
    return doc


def close(text, value):
    c = float(text.replace(",", ""))
    places = len(text.split(".")[1]) if "." in text else 0
    half = 0.5 * 10**-places + 1e-9
    return any(abs(c - v) <= half or abs(c - v) <= 0.005 * abs(v) for v in (value, value * 100))


def check(claim, comp):
    known = []
    for cite in claim.get("cites", []):
        try:
            v = walk(comp, cite["path"])
            cite["actual"] = v
            cite["ok"] = isinstance(v, int | float) and close(str(cite["value"]), v)
            if isinstance(v, int | float):
                known.append(float(v))
        except (KeyError, TypeError):
            cite["actual"], cite["ok"] = None, False
    text = NAMES.sub(" ", claim["text"])
    loose = [n for n in NUMBER.findall(text) if not any(close(n, k) for k in known)]
    claim["unbacked"] = loose
    claim["supported"] = all(c["ok"] for c in claim.get("cites", [])) and not loose
    html = claim["text"].replace("&", "&amp;").replace("<", "&lt;")
    for n in sorted(set(loose), key=len, reverse=True):
        html = re.sub(
            rf"(?<![\w.]){re.escape(n)}(?![\w])", f'<span class="unbacked">{n}</span>', html
        )
    claim["html"] = html
    return claim


def main():
    data = Path(sys.argv[1])
    model = sys.argv[2] if len(sys.argv) > 2 else "sonnet"
    comp = comparison(json.loads((data / "meta.json").read_text()))
    if model == "--recheck":
        out = json.loads((data / "ai.json").read_text())
        for scene, rec in out["scenes"].items():
            rec["claims"] = [check(c, comp) for c in rec["claims"]]
            rec["supported"] = sum(c["supported"] for c in rec["claims"])
            for c in rec["claims"]:
                print(scene, "OK " if c["supported"] else "BAD", c["unbacked"], c["text"])
        (data / "ai.json").write_text(json.dumps(out, indent=1))
        return
    run = subprocess.run(  # noqa: S603 (an argument list, no shell; the prompt is ours)
        [
            shutil.which("claude") or "claude",
            "-p",
            PROMPT + json.dumps(comp, indent=1),
            "--model",
            model,
            "--output-format",
            "json",
            "--tools",
            "",
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
        "usage": {k: raw.get("usage", {}).get(k) for k in USAGE},
        "scenes": {},
    }
    for scene, claims in doc["scenes"].items():
        checked = [check(c, comp) for c in claims]
        out["scenes"][scene] = {
            "claims": checked,
            "supported": sum(c["supported"] for c in checked),
        }
        for c in checked:
            print(scene, "OK " if c["supported"] else "BAD", c["unbacked"], c["text"])
    (data / "ai.json").write_text(json.dumps(out, indent=1))
    (data / "comparison.json").write_text(json.dumps(comp, indent=1))
    print("cost", out["cost_usd"])


if __name__ == "__main__":
    main()
