"""`recon` command line. The reconstruction backend arrives with its prototype's graduation; today
the CLI reads a capture set and writes the COLMAP model the backend starts from."""

import argparse
import json
import sys
from pathlib import Path

from recon import __version__, capture_set


def _inspect(args: argparse.Namespace) -> int:
    cs = capture_set.load(args.capture_set)
    posed = [f for f in cs.frames if f.position is not None]
    summary = {
        "manifest": cs.manifest["manifest"],
        "run_id": cs.manifest.get("run_id"),
        "frame": cs.frame_name,
        "pose_convention": vars(cs.convention),
        "images": len(cs.frames),
        "posed": len(posed),
        "pose_sources": sorted({f.pose_source or "none" for f in posed}),
        "sensors": sorted(cs.cameras),
        "stale_checksums": capture_set.stale_image_checksums(cs),
    }
    print(json.dumps(summary, indent=2))
    return 1 if summary["stale_checksums"] else 0


def _colmap_model(args: argparse.Namespace) -> int:
    cs = capture_set.load(args.capture_set)
    n = capture_set.write_colmap_text(cs, args.out)
    print(f"wrote {n} posed images to {args.out} (world-to-camera, OpenCV axes, z-up)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="recon")
    parser.add_argument("--version", action="version", version=f"recon {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect", help="read a capture set and summarise it")
    p.add_argument("capture_set", type=Path)
    p.set_defaults(func=_inspect)
    p = sub.add_parser("colmap-model", help="write the set's poses as a COLMAP text model")
    p.add_argument("capture_set", type=Path)
    p.add_argument("out", type=Path)
    p.set_defaults(func=_colmap_model)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except capture_set.CaptureSetError as exc:
        print(f"recon: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
