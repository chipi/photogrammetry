import hashlib
import json
import math
import random
from pathlib import Path

import pytest

from recon import capture_set as cs
from recon.cli import main

GL = cs.PoseConvention(camera_axes="opengl")
CV = cs.PoseConvention(camera_axes="opencv")
CAM = cs.Camera("cam0", "pinhole", 640, 480, 500.0, 500.0, 320.0, 240.0)


def close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b, strict=True))


def project(pos, quat, conv, point):
    rot, trans = cs.cam_from_world(pos, quat, conv)
    return cs.project(rot, trans, CAM, point)


def rand_quat(rng):
    return tuple(rng.uniform(-1, 1) for _ in range(4))


@pytest.mark.unit
def test_quaternion_matrix_round_trip():
    rng = random.Random(3)  # noqa: S311
    for _ in range(200):
        q = rand_quat(rng)
        n = math.sqrt(sum(c * c for c in q))
        q = tuple(c / n for c in q)
        back = cs.matrix_to_quat(cs.quat_to_matrix(*q))
        sign = 1 if q[3] >= 0 else -1
        assert close(back, tuple(sign * c for c in q), 1e-9)


@pytest.mark.unit
def test_quaternion_is_normalised_and_zero_refused():
    assert close(sum(cs.quat_to_matrix(0, 0, 0, 5), ()), sum(cs.IDENTITY, ()))
    with pytest.raises(cs.CaptureSetError):
        cs.quat_to_matrix(0, 0, 0, 0)


@pytest.mark.unit
def test_quaternion_xyzw_order_is_the_wire_order():
    # 90 degrees about +z: (x, y, z, w) = (0, 0, sin45, cos45) turns +x into +y.
    s = math.sqrt(0.5)
    rot = cs.quat_to_matrix(0, 0, s, s)
    assert close(cs.matvec(rot, (1, 0, 0)), (0, 1, 0))
    # The same numbers read as [w, x, y, z] would be a rotation about x: the order matters.
    wrong = cs.quat_to_matrix(s, 0, 0, s)
    assert not close(cs.matvec(wrong, (1, 0, 0)), (0, 1, 0))


@pytest.mark.unit
def test_opengl_camera_at_identity_looks_down_minus_z():
    u, v, depth = project((0, 0, 0), (0, 0, 0, 1), GL, (0, 0, -5))
    assert (u, v, depth) == pytest.approx((320.0, 240.0, 5.0))
    assert cs.project(*cs.cam_from_world((0, 0, 0), (0, 0, 0, 1), GL), CAM, (0, 0, 5))[2] < 0


@pytest.mark.unit
def test_opencv_camera_at_identity_looks_down_plus_z():
    u, v, depth = project((0, 0, 0), (0, 0, 0, 1), CV, (0, 0, 5))
    assert (u, v, depth) == pytest.approx((320.0, 240.0, 5.0))


@pytest.mark.unit
def test_known_robot_pose_in_a_z_up_frame():
    # Blender-style camera at (1, 2, 0.5) facing world +x, +Y of the camera up the world's +z:
    # camera x axis = world -y, camera y axis = world +z, camera -z (view) = world +x.
    rot_c2w = ((0, 0, -1), (-1, 0, 0), (0, 1, 0))
    quat = cs.matrix_to_quat(rot_c2w)
    pos = (1.0, 2.0, 0.5)
    # Straight ahead: lands on the principal point.
    assert project(pos, quat, GL, (6.0, 2.0, 0.5))[:2] == pytest.approx((320.0, 240.0))
    # Right of the view direction when facing +x is world -y: larger u.
    assert project(pos, quat, GL, (6.0, 1.0, 0.5))[0] == pytest.approx(320.0 + 500 * 1 / 5)
    # World up is image up: smaller v.
    assert project(pos, quat, GL, (6.0, 2.0, 1.5))[1] == pytest.approx(240.0 - 500 * 1 / 5)


@pytest.mark.unit
def test_converted_rotation_is_proper_and_centre_is_preserved():
    rng = random.Random(11)  # noqa: S311
    for conv in (GL, CV, cs.PoseConvention(camera_axes="opengl", world_up="+y")):
        for _ in range(50):
            pos = tuple(rng.uniform(-5, 5) for _ in range(3))
            rot, trans = cs.cam_from_world(pos, rand_quat(rng), conv)
            assert cs.det(rot) == pytest.approx(1.0)
            assert close(sum(cs.matmul(rot, cs.transpose(rot)), ()), sum(cs.IDENTITY, ()))
            want = cs.matvec(cs.YUP_TO_ZUP, pos) if conv.world_up == "+y" else pos
            assert close(cs.camera_centre(rot, trans), want)


@pytest.mark.unit
def test_handedness_conversion_keeps_right_handed_axes():
    assert cs.det(cs.GL_TO_CV) == 1.0
    assert cs.det(cs.YUP_TO_ZUP) == 1.0
    # y-up world: up is +y; after conversion it is +z.
    assert cs.matvec(cs.YUP_TO_ZUP, (0, 1, 0)) == (0, 0, 1)
    # Cross product of x and y stays z, in both worlds (right-handed).
    x, y = cs.matvec(cs.YUP_TO_ZUP, (1, 0, 0)), cs.matvec(cs.YUP_TO_ZUP, (0, 1, 0))
    cross = (x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0])
    assert cross == cs.matvec(cs.YUP_TO_ZUP, (0, 0, 1))


@pytest.mark.unit
def test_y_up_world_places_a_point_like_the_same_scene_in_z_up():
    # The same camera and point described in a y-up world and in the z-up world agree in pixels.
    quat_zup, pos_zup, pt_zup = (0.0, 0.0, 0.0, 1.0), (1.0, 2.0, 3.0), (1.0, 2.0, -2.0)
    # Express the same scene in y-up: apply the inverse of YUP_TO_ZUP to everything.
    inv = cs.transpose(cs.YUP_TO_ZUP)
    pos_y, pt_y = cs.matvec(inv, pos_zup), cs.matvec(inv, pt_zup)
    quat_y = cs.matrix_to_quat(cs.matmul(inv, cs.quat_to_matrix(*quat_zup)))
    a = project(pos_zup, quat_zup, GL, pt_zup)
    conv_y = cs.PoseConvention(camera_axes="opengl", world_up="+y")
    # Points live in the converted (z-up) world once the pose is converted.
    b = project(pos_y, quat_y, conv_y, cs.matvec(cs.YUP_TO_ZUP, pt_y))
    assert close(a, b, 1e-9)


@pytest.mark.unit
def test_world_to_camera_records_equal_camera_to_world_records():
    rng = random.Random(5)  # noqa: S311
    for _ in range(20):
        pos, quat = tuple(rng.uniform(-3, 3) for _ in range(3)), rand_quat(rng)
        rot_c2w = cs.quat_to_matrix(*quat)
        w2c_rot = cs.transpose(rot_c2w)
        w2c_t = cs.matvec(w2c_rot, tuple(-c for c in pos))
        w2c_quat = cs.matrix_to_quat(w2c_rot)
        a = cs.cam_from_world(pos, quat, GL)
        b = cs.cam_from_world(w2c_t, w2c_quat, cs.PoseConvention("world_to_camera", "opengl"))
        assert close(sum(a[0], ()), sum(b[0], ()), 1e-9)
        assert close(a[1], b[1], 1e-9)


@pytest.mark.unit
def test_unknown_or_left_handed_convention_refused():
    with pytest.raises(cs.CaptureSetError):
        cs.PoseConvention(handedness="left").validate()
    with pytest.raises(cs.CaptureSetError):
        cs.PoseConvention(camera_axes="sideways").validate()


def write_set(root: Path, manifest_version=1, conv=None, n=2, with_pose=True) -> Path:
    (root / "images").mkdir(parents=True)
    images = []
    for i in range(1, n + 1):
        data = f"img{i}".encode()
        (root / f"images/{i:06d}.png").write_bytes(data)
        rec = {
            "index": i,
            "file": f"images/{i:06d}.png",
            "sensor": "cam0",
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        if with_pose:
            rec["pose"] = {
                "frame": "map",
                "source": "truth",
                "position": {"x": float(i), "y": 0.0, "z": 1.0},
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            }
        images.append(rec)
    manifest = {
        "manifest": manifest_version,
        "frame": {"name": "map"},
        "pose_convention": conv
        or {
            "direction": "camera_to_world",
            "camera_axes": "opengl",
            "world_up": "+z",
            "handedness": "right",
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    (root / "images.json").write_text(json.dumps({"images": images}))
    cam = {
        "model": "pinhole",
        "width": 640,
        "height": 480,
        "fx": 500,
        "fy": 500,
        "cx": 320,
        "cy": 240,
    }
    (root / "cameras.json").write_text(json.dumps({"cam0": cam}))
    return root


@pytest.mark.integration
def test_load_reads_a_set(tmp_path):
    s = cs.load(write_set(tmp_path / "set"))
    assert len(s.frames) == 2
    assert s.frame_name == "map"
    assert s.convention.camera_axes == "opengl"
    assert s.frames[0].position == (1.0, 0.0, 1.0)
    assert s.frames[0].quaternion_xyzw == (0.0, 0.0, 0.0, 1.0)
    assert s.cameras["cam0"].fx == 500.0
    assert cs.stale_image_checksums(s) == []


@pytest.mark.integration
def test_unknown_pose_convention_field_is_a_capture_set_error(tmp_path):
    conv = {"direction": "camera_to_world", "camera_axes": "opencv", "units": "mm"}
    with pytest.raises(cs.CaptureSetError, match="unknown field"):
        cs.load(write_set(tmp_path / "set", conv=conv))


@pytest.mark.integration
def test_newer_manifest_refused_older_accepted(tmp_path):
    with pytest.raises(cs.CaptureSetError, match="newer"):
        cs.load(write_set(tmp_path / "new", manifest_version=cs.SUPPORTED_MANIFEST + 1))
    assert cs.load(write_set(tmp_path / "ok", manifest_version=1))


@pytest.mark.integration
def test_missing_image_and_missing_sensor_refused(tmp_path):
    root = write_set(tmp_path / "set")
    (root / "images/000002.png").unlink()
    with pytest.raises(cs.CaptureSetError, match="missing"):
        cs.load(root)
    root = write_set(tmp_path / "set2")
    (root / "cameras.json").write_text("{}")
    with pytest.raises(cs.CaptureSetError, match="intrinsics"):
        cs.load(root)
    with pytest.raises(cs.CaptureSetError, match="not a capture set"):
        cs.load(tmp_path / "nowhere")


@pytest.mark.integration
def test_stale_checksum_detected_and_checksums_reported(tmp_path):
    s = cs.load(write_set(tmp_path / "set"))
    (s.root / "images/000001.png").write_bytes(b"changed")
    assert cs.stale_image_checksums(s) == ["images/000001.png"]
    sums = cs.input_checksums(s)
    assert set(sums) == {
        "manifest.json", "images.json", "cameras.json", "images/000001.png", "images/000002.png",
    }  # fmt: skip
    assert sums["images/000001.png"] == hashlib.sha256(b"changed").hexdigest()


@pytest.mark.integration
def test_write_colmap_text_has_converted_poses(tmp_path):
    s = cs.load(write_set(tmp_path / "set"))
    out = tmp_path / "model"
    assert cs.write_colmap_text(s, out) == 2
    assert (out / "cameras.txt").read_text().splitlines()[
        1
    ] == "1 PINHOLE 640 480 500.0 500.0 320.0 240.0"
    row = (out / "images.txt").read_text().splitlines()[2].split()
    assert row[0] == "1" and row[-2:] == ["1", "000001.png"]
    qw, qx, qy, qz, tx, ty, tz = (float(v) for v in row[1:8])
    # Identity OpenGL camera at (1, 0, 1): rotation is the 180-degree flip about x.
    assert (qw, qx, qy, qz) == pytest.approx((0.0, 1.0, 0.0, 0.0))
    assert (tx, ty, tz) == pytest.approx((-1.0, 0.0, 1.0))


@pytest.mark.integration
def test_poseless_frames_are_left_out_of_the_model(tmp_path):
    s = cs.load(write_set(tmp_path / "set", with_pose=False))
    assert cs.write_colmap_text(s, tmp_path / "model") == 0


@pytest.mark.integration
def test_cli_inspect_and_colmap_model(tmp_path, capsys):
    root = write_set(tmp_path / "set")
    assert main(["inspect", str(root)]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["images"] == 2 and summary["pose_sources"] == ["truth"]
    assert main(["colmap-model", str(root), str(tmp_path / "m")]) == 0
    assert (tmp_path / "m" / "images.txt").is_file()
    assert main(["inspect", str(tmp_path / "nowhere")]) == 2


@pytest.mark.integration
def test_write_colmap_text_uses_database_image_ids(tmp_path):
    s = cs.load(write_set(tmp_path / "set"))
    cs.write_colmap_text(s, tmp_path / "m", image_ids={"000001.png": 7, "000002.png": 3})
    rows = (tmp_path / "m" / "images.txt").read_text().splitlines()[2::2]
    assert [(r.split()[0], r.split()[-1]) for r in rows if r] == [
        ("7", "000001.png"),
        ("3", "000002.png"),
    ]
