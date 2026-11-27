"""RC-M5 tutor: the person's AI as a tutor beside each mini-lab, over the facts labs.js computes at
the lab's starting state (tutor_facts.mjs). One `claude -p` call per lab, checked by coach_lib.

    node tutor_facts.mjs data                 # facts, moves and the rule's answer per lab
    python3 tutor.py data ai [model] [lab]    # the AI tutor: data/ai_tutor.json
    python3 tutor.py data --recheck           # re-checks the recorded answers, no call
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coach_lib

EXTRA = (
    "- You are tutoring a learner in a mini-lab beside the term '{term}' of a photogrammetry "
    "primer. The lab is synthetic by design: its numbers come from a formula or a small "
    "simulation, not a measurement. The learner moved the controls to the state in the facts. "
    "Explain what they see and why in plain words, then suggest moves to try. Actions marked "
    '"lab" move the lab\'s controls; "capture" and "engine" are what the idea means for a '
    "real capture or the engine. Keep it short: a learner reads it beside the figure."
)


def main() -> None:
    data = Path(sys.argv[1])
    labs = json.loads((data / "tutor_facts.json").read_text())
    out_path = data / "ai_tutor.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else {}
    mode = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == "--recheck":
        for lab_id, doc in done.items():
            print("==", lab_id)
            doc = coach_lib.check(doc, labs[lab_id]["facts"], labs[lab_id]["actions"])
            coach_lib.report(doc)
        out_path.write_text(json.dumps(done, indent=1))
    elif mode == "ai":
        model = sys.argv[3] if len(sys.argv) > 3 else "sonnet"
        only = sys.argv[4] if len(sys.argv) > 4 else None
        for lab_id, lab in labs.items():
            if only and lab_id != only:
                continue
            print("==", lab_id)
            extra = EXTRA.format(term=lab["term"])
            doc = coach_lib.run(lab["facts"], lab["actions"], extra, None, model)
            doc["state"] = lab["state"]
            done[lab_id] = doc
            out_path.write_text(json.dumps(done, indent=1))
            coach_lib.report(doc)
    for lab_id, lab in labs.items():
        print("rule", lab_id.ljust(11), lab["rule"]["act"].ljust(15), lab["rule"]["see"])


if __name__ == "__main__":
    main()
