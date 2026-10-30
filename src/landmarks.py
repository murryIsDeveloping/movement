"""Landmark indices, the body subset drawn on the preview, its skeleton lines, and the in-frame check."""
from enum import IntEnum

import numpy as np


class L(IntEnum):
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28


# Face and finger landmarks excluded: noisy and irrelevant to body poses.
BODY = [
    L.NOSE,
    L.LEFT_SHOULDER, L.RIGHT_SHOULDER,
    L.LEFT_ELBOW, L.RIGHT_ELBOW,
    L.LEFT_WRIST, L.RIGHT_WRIST,
    L.LEFT_HIP, L.RIGHT_HIP,
    L.LEFT_KNEE, L.RIGHT_KNEE,
    L.LEFT_ANKLE, L.RIGHT_ANKLE,
]

SKELETON = [
    (L.LEFT_SHOULDER, L.RIGHT_SHOULDER),
    (L.LEFT_SHOULDER, L.LEFT_ELBOW), (L.LEFT_ELBOW, L.LEFT_WRIST),
    (L.RIGHT_SHOULDER, L.RIGHT_ELBOW), (L.RIGHT_ELBOW, L.RIGHT_WRIST),
    (L.LEFT_SHOULDER, L.LEFT_HIP), (L.RIGHT_SHOULDER, L.RIGHT_HIP),
    (L.LEFT_HIP, L.RIGHT_HIP),
    (L.LEFT_HIP, L.LEFT_KNEE), (L.LEFT_KNEE, L.LEFT_ANKLE),
    (L.RIGHT_HIP, L.RIGHT_KNEE), (L.RIGHT_KNEE, L.RIGHT_ANKLE),
]

# Joints the features read. If any is off screen or hidden, nothing fires. Ankles aren't read, so feet may be cut off.
IN_FRAME = [
    L.NOSE,
    L.LEFT_SHOULDER, L.RIGHT_SHOULDER,
    L.LEFT_ELBOW, L.RIGHT_ELBOW,
    L.LEFT_WRIST, L.RIGHT_WRIST,
    L.LEFT_HIP, L.RIGHT_HIP,
    L.LEFT_KNEE, L.RIGHT_KNEE,
]
MIN_VISIBILITY = 0.5


def out_of_frame(p: np.ndarray) -> list[str]:
    """IN_FRAME joints off the edge of the picture or hidden, as names ("left knee"). Visibility is column 3, if present."""
    vis = p[:, 3] if p.shape[1] > 3 else np.ones(len(p))
    return [L(i).name.lower().replace("_", " ") for i in IN_FRAME
            if vis[i] < MIN_VISIBILITY or not (0.0 <= p[i, 0] <= 1.0 and 0.0 <= p[i, 1] <= 1.0)]


class FrameWatch:
    """Pauses only once the body has been out of frame (or untracked) for `after` seconds straight, so a head
    leaving the top edge mid-jump doesn't pause, but walking up to the camera does."""

    def __init__(self, after: float = 0.5):
        self.after = after
        self.out_since: float | None = None

    def update(self, p: np.ndarray | None, t: float) -> tuple[bool, list[str]]:
        """(paused, joints out of frame now)."""
        missing = out_of_frame(p) if p is not None else []
        if p is not None and not missing:
            self.out_since = None
        elif self.out_since is None:
            self.out_since = t
        return self.out_since is not None and t - self.out_since >= self.after, missing
