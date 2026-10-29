"""config.yaml load/save."""
from pathlib import Path

import yaml

from src import paths
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


def load(path: Path = CONFIG) -> dict:
    if not path.exists():
        save(DEFAULT, path)
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    return {**DEFAULT, **cfg}


def save(cfg: dict, path: Path = CONFIG) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)


def poses_from(cfg: dict) -> list[Pose]:
    return [Pose.from_dict(d) for d in cfg.get("poses", [])]
