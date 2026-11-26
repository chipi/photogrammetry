"""RC-P13 buildings segment: OpenStreetMap's building footprints over the compared grid, as the
clean reference (the LiDAR has no building class and its rule keeps tree crowns).

OpenStreetMap data is ODbL; it is fetched into the run directory and never committed. The site is
in southern Sardinia: the dataset's coordinates are UTM zone 32N (EPSG:32632; zone 33 puts them in
the sea), so pyproj does the projection. It runs in a throwaway container, so nothing is installed:

    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/src:ro" \\
      -v ~/.cache/recce/runs/p13/buildings/usegeo1:/run python:3.12-slim \\
      sh -c "pip install -q pyproj numpy && python /src/fetch_osm.py /run"

Writes `osm_buildings.json`: each way's id, tags and outline in the run's local frame.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from pyproj import Transformer

OVERPASS = "https://overpass-api.de/api/interpreter"
MARGIN_M = 50


def main():
    run = Path(sys.argv[1])
    origin = np.array(json.loads((run / "frame.json").read_text())["origin"])
    g = np.load(run / "grids.npz")
    lo = g["lo"] - MARGIN_M + origin[:2]
    hi = g["lo"] + np.array(g["top"].shape) + MARGIN_M + origin[:2]
    to_ll = Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32632", always_xy=True)
    lon0, lat0 = to_ll.transform(lo[0], lo[1])
    lon1, lat1 = to_ll.transform(hi[0], hi[1])
    query = f"[out:json][timeout:60];way[building]({lat0},{lon0},{lat1},{lon1});out tags geom;"
    req = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "recce-prototype (RC-P13)"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (a fixed https URL)
        ways = json.load(r)["elements"]
    out = []
    for w in ways:
        lon = [p["lon"] for p in w["geometry"]]
        lat = [p["lat"] for p in w["geometry"]]
        x, y = to_utm.transform(lon, lat)
        xy = np.c_[x, y] - origin[:2]
        out.append({"id": w["id"], "tags": w.get("tags", {}), "xy": xy.round(3).tolist()})
    (run / "osm_buildings.json").write_text(json.dumps(out))
    print(f"OSM bbox lat {lat0:.5f}..{lat1:.5f} lon {lon0:.5f}..{lon1:.5f}: {len(out)} buildings")


if __name__ == "__main__":
    main()
