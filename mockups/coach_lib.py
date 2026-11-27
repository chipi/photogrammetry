"""The coach: the optional AI layer shared by the mock-ups (owner, 2026-11-27: "AI as a coach to
the operator: why things are as they are, and how to get to a better place").

The engine supplies the facts and a menu of actions it can carry out; the coach explains, picks
and orders actions into a plan, and says how the operator will know it worked. This module makes
the call and checks the answer: every number must match the fact it cites, and every plan step
must name an action from the menu. Without AI, each mock-up's own rule writes the plan from the
same facts.

The call runs `claude -p` with no MCP servers, no settings sources and its own system prompt, so
it carries only the prompt (RC-M4 measured the default context at about 60 times the cost).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

NUMBER = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])-?\d+(?:\.\d+)?")
NOT_NUMBERS = re.compile(
    r"DSC_\d+|RGT_\d+|\b[23]D\b|\b\d+(?:st|nd|rd|th)\b|RC-[PM]\d+|\bM\d\b"
    r"|\b[Ff]rames?,? \d+(?:(?:,| and) \d+)*"  # names and labels, not quantities
)
USAGE = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")

SYSTEM = "You coach the operator of a 3D reconstruction tool. You are precise and brief."

FRAME = """You are the optional coach of a 3D reconstruction tool; the person connected their own
AI and the tool works without you. Coach the operator: say why the result is the way it is, and
how to get to a better one.

Rules:
- Use only the facts below. Every number you write must cite its fact: the dot path (list items
  by index, as charts.0) and the value. Write a share as it appears, or times 100 with a percent
  sign. Each item is checked on its own: cite every number in that item, even one you cited in
  another item. A number with no fact behind it may not be written; leave it out.
- Every plan step names one action id from the menu; do not invent actions. Order the steps by
  what to do first.
- Say what is a guess. If the facts cannot answer something, say so in "unknown".
{extra}
End with one JSON object and nothing after it:
{{"headline": {{"text": "...", "cites": [{{"path": "a.b", "value": 1.0}}]}},
 "why": [{{"text": "...", "cites": []}}],
 "plan": [{{"action": "<id from the menu>", "text": "what to do and why", "expect": "what should
   change", "cites": []}}],
 "check": {{"text": "how the operator will know it worked", "cites": []}},
 "unknown": [{{"text": "...", "cites": []}}]}}

Facts:
{facts}

Action menu:
{actions}
"""


def walk(doc, path):
    for k in path.split("."):
        doc = doc[int(k)] if isinstance(doc, list) else doc[k]
    return doc


def close(text: str, value: float) -> bool:
    c = float(text.replace(",", ""))
    places = len(text.split(".")[1]) if "." in text else 0
    half = 0.5 * 10**-places + 1e-9
    return any(
        abs(c - v) <= half or abs(c - v) <= 0.005 * abs(v) for v in (value, value * 100, -value)
    )


def check_claim(claim: dict, facts: dict, actions: dict | None = None) -> dict:
    known = []
    for cite in claim.get("cites", []):
        try:
            v = walk(facts, cite["path"])
        except (KeyError, IndexError, ValueError, TypeError):
            v = None
        cite["actual"] = v
        cite["ok"] = isinstance(v, int | float) and close(str(cite.get("value")), float(v))
        if isinstance(v, int | float):
            known.append(float(v))
        # a threshold named in the cited fact ("share_seen_by_32_or_more") is backed by that cite,
        # and so are the other numbers of the record it sits in (a bin's bounds beside its median)
        try:
            parent = walk(facts, cite["path"].rsplit(".", 1)[0]) if "." in cite["path"] else {}
        except (KeyError, IndexError, ValueError, TypeError):
            parent = {}
        if isinstance(parent, dict):
            known += [float(x) for x in parent.values() if isinstance(x, int | float)]
        known += [float(x) for x in re.findall(r"(?<![a-z])\d+(?![a-z])", cite.get("path", ""))]
    text = " ".join(claim.get(k, "") for k in ("text", "expect"))
    numbers = NUMBER.findall(NOT_NUMBERS.sub(" ", text))
    claim["unbacked"] = [n for n in numbers if not any(close(n, k) for k in known)]
    bad_cite = not all(c["ok"] for c in claim.get("cites", []))
    claim["action_ok"] = None if actions is None else claim.get("action") in actions
    if claim["unbacked"] or bad_cite or claim["action_ok"] is False:
        claim["status"] = "unsupported"
    else:
        claim["status"] = "supported" if claim.get("cites") else "judgement"
    return claim


def check(doc: dict, facts: dict, actions: dict) -> dict:
    doc["headline"] = check_claim(doc["headline"], facts)
    doc["why"] = [check_claim(c, facts) for c in doc.get("why", [])]
    doc["plan"] = [check_claim(c, facts, actions) for c in doc.get("plan", [])]
    doc["check"] = check_claim(doc["check"], facts)
    doc["unknown"] = [check_claim(c, facts) for c in doc.get("unknown", [])]
    return doc


def claims(doc: dict) -> list[dict]:
    return [doc["headline"], *doc["why"], *doc["plan"], doc["check"], *doc["unknown"]]


def run(
    facts: dict,
    actions: dict,
    extra: str = "",
    images: list[Path] | None = None,
    model: str = "sonnet",
) -> dict:
    prompt = FRAME.format(
        extra=extra, facts=json.dumps(facts, indent=1), actions=json.dumps(actions, indent=1)
    )
    cmd = [shutil.which("claude") or "claude", "-p", "", "--model", model]
    if images:
        prompt += "\nImages to look at with the Read tool:\n" + "\n".join(map(str, images))
        dirs = sorted({str(p.parent) for p in images})
        cmd += ["--tools", "Read", "--allowedTools", "Read", "--add-dir", *dirs]
    else:
        cmd += ["--tools", ""]
    cmd[2] = prompt
    cmd += [
        "--output-format",
        "json",
        "--strict-mcp-config",
        "--setting-sources",
        "",
        "--system-prompt",
        SYSTEM,
        "--max-budget-usd",
        "0.50",
    ]
    out = subprocess.run(  # noqa: S603 (an argument list, no shell; the prompt is ours)
        cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True
    )
    raw = json.loads(out.stdout)
    text = raw["result"]
    doc = json.loads(text[text.index("{") : text.rindex("}") + 1])
    doc = check(doc, facts, actions)
    doc["model"] = f"Claude {model.capitalize()}"
    doc["cost_usd"] = raw.get("total_cost_usd")
    doc["usage"] = {k: raw.get("usage", {}).get(k) for k in USAGE}
    return doc


def recheck(path: Path, facts: dict, actions: dict) -> dict:
    doc = check(json.loads(path.read_text()), facts, actions)
    path.write_text(json.dumps(doc, indent=1))
    return doc


def report(doc: dict) -> None:
    for c in claims(doc):
        tag = c.get("action") or ""
        print(c["status"].ljust(11), tag.ljust(18), c["unbacked"], c["text"][:110])
    if "cost_usd" in doc:
        print("cost", doc["cost_usd"], doc.get("usage"))
