"""config.yaml load/save."""
from pathlib import Path

import yaml

from src import library, paths
from src.keys import valid_key
from src.rules import Pose

ROOT = paths.resource_root()
CONFIG = paths.config_path()

DEFAULT = {
    "camera": {"index": 0, "width": 640, "height": 480},
    "model": "models/pose_landmarker_lite.task",
    "port": 8765,
    "send_keys": False,
    "poses": [
        {"name": "jog", "key": "w", "conditions": [{"feature": "step_cadence", "op": ">", "value": 1.0}]},
        {"name": "jump", "key": "space", "conditions": [{"feature": "hip_rise", "op": ">", "value": 0.15}]},
        {"name": "strafe right", "key": "e", "conditions": [{"feature": "right_arm_raise", "op": ">", "value": 70},
                                                            {"feature": "right_arm_raise", "op": "<", "value": 120}]},
        {"name": "strafe left", "key": "q", "conditions": [{"feature": "left_arm_raise", "op": ">", "value": 70},
                                                           {"feature": "left_arm_raise", "op": "<", "value": 120}]},
    ],
}


FIRST_RUN_GROUP = "wow hunter"   # built-in group a new install starts from: all its presets are tested


def first_run() -> dict:
    """DEFAULT with the poses of FIRST_RUN_GROUP, linked to the library. Falls back to DEFAULT's own poses if
    presets.yaml is missing, broken or no longer has that group, so a first launch never fails."""
    try:
        poses = library.group_poses(FIRST_RUN_GROUP)
        if poses:
            return {**DEFAULT, "poses": poses}
    except Exception as e:
        print(f"first run: can't load built-in group {FIRST_RUN_GROUP!r} ({e}), using the basic poses")
    return DEFAULT


def load(path: Path = CONFIG) -> dict:
    if not path.exists():
        save(first_run(), path)
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    merged = {**DEFAULT, **cfg}
    for k, v in DEFAULT.items():   # one level deep, so a camera block that only sets index keeps width and height
        if isinstance(v, dict):
            merged[k] = {**v, **(cfg.get(k) or {})}
    return merged


def save(cfg: dict, path: Path = CONFIG) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def poses_from(cfg: dict) -> list[Pose]:
    return [Pose.from_dict(d) for d in cfg.get("poses", [])]


def poses_lenient(cfg: dict) -> list[Pose]:
    """At startup: a bad pose is not fatal. A bad key (e.g. half-typed by an older build) keeps the pose, disabled with
    key 1, so its tuning survives; anything else wrong skips it. cfg is updated to match, so an export or the next save
    keeps the same poses."""
    good, poses = [], []
    for d in cfg.get("poses", []):
        if not valid_key(str(d.get("key", ""))):
            print(f"config.yaml: pose {d.get('name')!r}: unknown key {d.get('key')!r}, pose disabled with key 1")
            d = {**d, "key": "1", "enabled": False}
        try:
            poses.append(Pose.from_dict(d))
            good.append(d)
        except (ValueError, KeyError, TypeError) as e:
            print(f"config.yaml: {e}, pose skipped")
    cfg["poses"] = good
    return poses
