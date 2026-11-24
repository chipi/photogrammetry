"""RC-P4: write <workspace>/images_<factor>/ next to images/, as gsplat's trainer expects.

Usage: downscale_images.py <workspace> <factor>
The Mip-NeRF 360 scenes ship these folders; the COLMAP dense workspace does not.
"""

import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    ws, factor = Path(sys.argv[1]), int(sys.argv[2])
    src, dst = ws / "images", ws / f"images_{factor}"
    n = 0
    for p in src.rglob("*"):
        if p.is_file():
            out = dst / p.relative_to(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(p) as im:
                im.resize((im.width // factor, im.height // factor), Image.LANCZOS).save(
                    out, quality=95
                )
            n += 1
    print(f"wrote {n} images to {dst}")


if __name__ == "__main__":
    main()
