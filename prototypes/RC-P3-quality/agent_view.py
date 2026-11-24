"""Print what an agent sees through the three tools for one run (no LLM call).

uv run python agent_view.py kicker/heldout [--weakest 3]
"""

import argparse
import json

import tools


def show(title, obj):
    print(f"\n== {title}\n{json.dumps(obj, indent=2)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", help="run id (scene/phase) or path to a run folder")
    ap.add_argument("--weakest", type=int, default=2, help="regions to open with get_region")
    args = ap.parse_args()

    show(f"get_summary({args.run!r})", tools.get_summary(args.run))
    listing = tools.list_regions(args.run)
    show(f"list_regions({args.run!r})", listing)
    for row in listing["regions"][: args.weakest]:
        show(f"get_region({args.run!r}, {row['id']!r})", tools.get_region(args.run, row["id"]))


if __name__ == "__main__":
    main()
