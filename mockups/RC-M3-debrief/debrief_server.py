"""RC-M3: the debrief agent's MCP server. RC-P3's three read tools unchanged, one read tool for
the measured products (RC-P4, RC-P6) and three scene-editing tools (idea 18) that write the
agent's labels and ghost cameras to data/annotations.json, which the page draws and the person
can move or delete.

Run under RC-P3's uv project, which has the MCP SDK:
    uv run --directory prototypes/RC-P3-quality python ../../mockups/RC-M3-debrief/debrief_server.py
"""

import json
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "prototypes/RC-P3-quality"))
import plan_shots
import tools

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ANNOTATIONS = DATA / "annotations.json"


def _annotations() -> list[dict]:
    return json.loads(ANNOTATIONS.read_text()) if ANNOTATIONS.is_file() else []


def _save(items: list[dict]) -> None:
    ANNOTATIONS.write_text(json.dumps(items, indent=1))


def get_products() -> dict:
    """Measured products of this run: the dense cloud and mesh checked against the ETH3D laser
    scan at 2, 5 and 10 cm (F1, accuracy, completeness as 0..1 shares), the texture's resolution
    and seams, the photos' sharpness and exposure spread, and the browser viewer's frame rates.
    The scan check is not available in the field; say so when you use these numbers."""
    return json.loads((DATA / "products.json").read_text())


def list_cameras(region_id: str | None = None) -> dict:
    """Where the photos were taken: each camera's centre [x, y, z] in the scene frame (metres)
    and the direction it looked. With region_id, only the cameras whose photos see that region.
    Use it to put a new shot where a photographer can stand."""
    scene = json.loads((DATA / "scene.json").read_text())
    names = None
    if region_id:
        names = {i["name"] for i in tools.get_region(scene["run"], region_id)["images_seeing"]}
    cams = [
        {
            "name": c["name"],
            "centre": c["centre"],
            "looking": [round(row[2], 3) for row in c["rotation"]],
        }
        for c in scene["cameras"]
        if names is None or c["name"] in names
    ]
    return {"cameras": cams, "total": len(cams)}


def get_engine_debrief() -> dict:
    """The debrief the engine wrote without AI: its sentences, by section, and its readiness
    verdicts. Build on it; do not repeat it."""
    doc = json.loads((DATA / "rules.json").read_text())
    return {
        "sections": [
            {"heading": s["heading"], "sentences": [c["text"] for c in s["claims"]]}
            for s in doc["sections"]
        ],
        "readiness": [
            {k: r[k] for k in ("use", "status", "requires", "because")} for r in doc["readiness"]
        ],
    }


def suggest_shots(region_id: str) -> dict:
    """The engine's suggested spot for a new photo of a region, from geometry alone: at hand
    height, inside the area already walked, on the side the surface faces, with a clear line of
    sight and a new direction. Returns position and look_at [x, y, z] (metres), the new angle,
    the distance, the nearest photo already taken, or found=false with the reason. Use this
    position for a ghost camera; do not invent one."""
    scene, xyz, point_region = plan_shots.load(DATA)
    return plan_shots.suggest(tools.get_region(scene["run"], region_id), scene, xyz, point_region)


def place_label(text: str, position: list[float], region_id: str | None = None) -> dict:
    """Place a short label in the scene at position [x, y, z] (scene frame, metres), optionally
    tied to a region id. The person sees it, can move it and can delete it."""
    items = _annotations()
    item = {
        "id": f"A{len(items) + 1:02d}",
        "kind": "label",
        "text": text,
        "position": position,
        "region": region_id,
    }
    _save([*items, item])
    return item


def place_camera(position: list[float], look_at: list[float], reason: str) -> dict:
    """Place a ghost camera: where a new photo should be taken from (position) and what it should
    look at, both [x, y, z] in the scene frame, with a one-line reason."""
    items = _annotations()
    item = {
        "id": f"A{len(items) + 1:02d}",
        "kind": "camera",
        "position": position,
        "look_at": look_at,
        "reason": reason,
    }
    _save([*items, item])
    return item


def list_annotations() -> list[dict]:
    """The labels and ghost cameras placed so far, including any the person moved."""
    return _annotations()


server = MCPServer(
    "recce-debrief",
    instructions=(
        "Quality state and products of one reconstruction, plus tools to place labels and ghost "
        "cameras in its scene. Read with get_summary, list_regions, get_region (run id "
        "'courtyard/full'), get_products, list_cameras and suggest_shots; place with "
        "place_label and place_camera."
    ),
)
for fn in (
    tools.get_summary,
    tools.list_regions,
    tools.get_region,
    get_products,
    get_engine_debrief,
    list_cameras,
    suggest_shots,
    place_label,
    place_camera,
    list_annotations,
):
    server.tool()(fn)

if __name__ == "__main__":
    server.run("stdio")
