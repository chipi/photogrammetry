import json
import struct
from pathlib import Path

import pytest

from recon import capture_set as cs
from recon import components as comp
from recon.cli import main
from test_capture_set import write_set

POSE = (1.0, 0.0, 0.0, 0.0, 0.5, -0.25, 2.0)  # qw qx qy qz tx ty tz


def write_bin(folder: Path, images: dict[str, list[int]]) -> Path:
    """images.bin: name -> the point3D id of each 2-D point (-1 = unmatched)."""
    folder.mkdir(parents=True)
    out = struct.pack("<Q", len(images))
    for image_id, (name, ids) in enumerate(images.items(), start=1):
        out += struct.pack("<I7di", image_id, *POSE, 1) + name.encode() + b"\0"
        out += struct.pack("<Q", len(ids))
        out += b"".join(struct.pack("<ddq", 10.0 * k, 5.0, i) for k, i in enumerate(ids))
    (folder / "images.bin").write_bytes(out)
    return folder


def write_txt(folder: Path, images: dict[str, list[int]]) -> Path:
    folder.mkdir(parents=True)
    lines = ["# Image list with two lines of data per image:"]
    for image_id, (name, ids) in enumerate(images.items(), start=1):
        lines.append(f"{image_id} {' '.join(map(str, POSE))} 1 {name}")
        lines.append(" ".join(f"{10.0 * k} 5.0 {i}" for k, i in enumerate(ids)))
    (folder / "images.txt").write_text("\n".join(lines) + "\n")
    return folder


@pytest.mark.integration
def test_binary_and_text_models_read_the_same(tmp_path):
    images = {"a.png": [3, -1, 7], "b.png": [-1, -1], "c d.png": []}
    b = comp.read_model(write_bin(tmp_path / "bin", images))
    t = comp.read_model(write_txt(tmp_path / "txt", images))
    assert [(i.name, i.observed_points) for i in b] == [("a.png", 2), ("b.png", 0), ("c d.png", 0)]
    assert [(i.name, i.observed_points) for i in t] == [(i.name, i.observed_points) for i in b]
    assert b[0].cam_from_world_quat_wxyz == POSE[:4] and b[0].translation == POSE[4:]


@pytest.mark.integration
def test_a_pose_without_points_is_not_registered(tmp_path):
    root = tmp_path / "sparse"
    write_bin(root / "0", {"frame_1.png": [5], "frame_2.png": [-1]})
    assert comp.read_components(root) == {"0": {"frame_1.png"}}


@pytest.mark.unit
def test_breaks_gaps_and_shared_photos():
    names = [f"frame_{i}.png" for i in range(1, 9)]
    c = {
        "0": {names[0], names[1], names[2], names[5]},
        "1": {names[3], names[4], names[5], names[7]},
    }
    # frame_7 is in no component, so 6 -> 8 is a gap inside component 1.
    r = comp.report(c)
    assert (r["photos"], r["registered"], r["unregistered"]) == (7, 7, 0)
    assert r["shared_photos"] == {"0-1": 1}
    assert [(b["from_photo"], b["to_photo"]) for b in r["breaks"]] == [
        ("frame_3.png", "frame_4.png")
    ]
    assert r["breaks"][0]["from_components"] == ["0"] and r["breaks"][0]["to_components"] == ["1"]
    assert r["one_model"] is False
    # Without a capture set an unregistered photo is invisible: the order holds registered ones.
    assert r["gaps_within_component"] == []


@pytest.mark.unit
def test_natural_order_puts_frame_9_before_frame_10():
    c = {"0": {"frame_9.png", "frame_10.png"}, "1": {"frame_11.png"}}
    r = comp.report(c)
    assert r["breaks"][0]["from_photo"] == "frame_10.png"
    assert r["breaks"][0]["to_photo"] == "frame_11.png"


@pytest.mark.integration
def test_capture_set_gives_order_unregistered_runs_and_places(tmp_path):
    s = cs.load(write_set(tmp_path / "set", n=6))
    c = {"0": {"000001.png", "000002.png"}, "1": {"000003.png", "000006.png"}}
    r = comp.report(c, s)
    assert (r["photos"], r["registered"], r["unregistered"]) == (6, 4, 2)
    (brk,) = r["breaks"]
    assert (brk["from_photo"], brk["to_photo"], brk["unregistered_between"]) == (
        "000002.png",
        "000003.png",
        0,
    )
    # write_set places photo i at x = i with one orientation: one metre apart, no turn.
    assert brk["where"]["moved_m"] == 1.0 and brk["where"]["turned_deg"] == 0.0
    assert brk["where"]["pose_source"] == "truth"
    (gap,) = r["gaps_within_component"]
    assert (gap["from_photo"], gap["to_photo"], gap["unregistered_between"]) == (
        "000003.png",
        "000006.png",
        2,
    )


@pytest.mark.integration
def test_one_model_needs_every_photo_in_one_component(tmp_path):
    s = cs.load(write_set(tmp_path / "set", n=3))
    every = {"0": {"000001.png", "000002.png", "000003.png"}}
    assert comp.report(every, s)["one_model"] is True
    assert comp.report({"0": {"000001.png", "000003.png"}}, s)["one_model"] is False


@pytest.mark.integration
def test_a_registered_photo_missing_from_the_set_is_refused(tmp_path):
    s = cs.load(write_set(tmp_path / "set", n=2))
    with pytest.raises(comp.ModelError):
        comp.report({"0": {"000001.png", "stray.png"}}, s)


@pytest.mark.integration
def test_cli_writes_the_report(tmp_path, capsys):
    root = tmp_path / "sparse"
    write_bin(root / "0", {"frame_1.png": [1], "frame_2.png": [2]})
    write_txt(root / "1", {"frame_3.png": [4]})
    out = tmp_path / "report.json"
    assert main(["components", str(root), "--out", str(out)]) == 0
    r = json.loads(out.read_text())
    assert r["components"] == [{"component": "0", "photos": 2}, {"component": "1", "photos": 1}]
    assert len(r["breaks"]) == 1
    assert json.loads(capsys.readouterr().out) == r


@pytest.mark.integration
def test_cli_reports_a_folder_without_a_model(tmp_path, capsys):
    (tmp_path / "empty" / "0").mkdir(parents=True)
    assert main(["components", str(tmp_path / "empty")]) == 2
    assert "no images.bin or images.txt" in capsys.readouterr().err
