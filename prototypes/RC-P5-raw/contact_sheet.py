"""Write one side-by-side JPEG of an image under the three routes, for a visual check."""

import sys

import numpy as np
import pycolmap
from common import ROUTES, RUNS, route_images, write_jpeg

scene = sys.argv[1]
stem = sys.argv[2]
tiles = []
for route in ROUTES:
    path = next(p for p in route_images(scene, route) if p.stem == stem)
    bmp = pycolmap.Bitmap.read(str(path), as_rgb=True)
    bmp.rescale(756, 504)
    tiles.append(bmp.to_array())
write_jpeg(RUNS / scene / f"contact_{stem}.jpg", np.concatenate(tiles, axis=1))
print(RUNS / scene / f"contact_{stem}.jpg")
