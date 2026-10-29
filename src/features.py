"""Per-frame body measurements. All lengths in torso units, angles in degrees."""
import math
from collections import deque

import numpy as np

from src.landmarks import L

# name -> (description, unit) shown in the GUI
FEATURES = {
    "hip_rise":         ("Hips moved up within the last 0.4s (jump)", "torso"),
    "hip_drop":         ("Hips below standing height (squat)", "torso"),
    "left_knee_lift":   ("Left knee raised from standing", "torso"),
    "right_knee_lift":  ("Right knee raised from standing", "torso"),
    "step_cadence":     ("Alternating knee lifts per second (jog)", "steps/s"),
    "left_arm_raise":   ("Left upper arm from hanging: 0 down, 90 out, 180 up", "deg"),
    "right_arm_raise":  ("Right upper arm from hanging: 0 down, 90 out, 180 up", "deg"),
    "left_arm_angle":   ("Left elbow angle: 180 straight", "deg"),
    "right_arm_angle":  ("Right elbow angle: 180 straight", "deg"),
    "left_wrist_out":   ("Left wrist sideways from shoulder (+ = away from body)", "torso"),
    "right_wrist_out":  ("Right wrist sideways from shoulder (+ = away from body)", "torso"),
    "left_wrist_up":    ("Left wrist above shoulder", "torso"),
    "right_wrist_up":   ("Right wrist above shoulder", "torso"),
    "wrists_distance":  ("Distance between wrists", "torso"),
    "wrist_low":        ("Lowest wrist below hips (touch ground)", "torso"),
    "lean":             ("Shoulders sideways of hips (+ = your right... mirrored view)", "torso"),
    "head_tilt":        ("Nose sideways of shoulder centre", "torso"),
}


def _angle(a, b, c) -> float:
    """Angle at b in degrees."""
    v1, v2 = a - b, c - b
    cosang = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosang))))


def _raise(shoulder, elbow) -> float:
    """Upper arm angle from straight down. y axis points down in image coords."""
    v = elbow - shoulder
    down = np.array([0.0, 1.0])
    return _angle(shoulder + down, shoulder, elbow) if np.linalg.norm(v) > 1e-9 else 0.0


class _Baseline:
    """Tracks the resting value: snaps down to new lows, drifts up slowly."""

    def __init__(self, rate=0.01):
        self.rate = rate
        self.v = None

    def update(self, x: float) -> float:
        if self.v is None or x > self.v:
            self.v = x
        else:
            self.v += (x - self.v) * self.rate
        return self.v


class FeatureEngine:
    def __init__(self, rise_window=0.4):
        self.rise_window = rise_window
        self.hip_hist: deque[tuple[float, float]] = deque()
        self.hip_base = _Baseline()
        self.knee_base = {L.LEFT_KNEE: _Baseline(), L.RIGHT_KNEE: _Baseline()}
        self.knee_up = {L.LEFT_KNEE: False, L.RIGHT_KNEE: False}
        self.last_leg = None
        self.steps: deque[float] = deque(maxlen=6)

    def reset_baselines(self):
        self.hip_base = _Baseline()
        self.knee_base = {L.LEFT_KNEE: _Baseline(), L.RIGHT_KNEE: _Baseline()}

    def update(self, p: np.ndarray, t: float) -> dict[str, float]:
        xy = p[:, :2]
        ls, rs = xy[L.LEFT_SHOULDER], xy[L.RIGHT_SHOULDER]
        lh, rh = xy[L.LEFT_HIP], xy[L.RIGHT_HIP]
        shoulders, hips = (ls + rs) / 2, (lh + rh) / 2
        torso = float(np.linalg.norm(shoulders - hips)) or 1e-6
        u = lambda v: float(v) / torso

        f: dict[str, float] = {}

        # vertical hip motion
        hy = float(hips[1])
        self.hip_hist.append((t, hy))
        while self.hip_hist and t - self.hip_hist[0][0] > self.rise_window:
            self.hip_hist.popleft()
        f["hip_rise"] = u(max(h[1] for h in self.hip_hist) - hy)
        f["hip_drop"] = self._hip_drop(hy, torso)

        # knees
        for side, knee, hip in (("left", L.LEFT_KNEE, L.LEFT_HIP), ("right", L.RIGHT_KNEE, L.RIGHT_HIP)):
            rel = float(xy[knee, 1] - xy[hip, 1])
            base = self.knee_base[knee].update(rel)
            lift = u(base - rel)
            f[f"{side}_knee_lift"] = lift
            up = lift > 0.15
            if up and not self.knee_up[knee] and self.last_leg != knee:
                self.steps.append(t)
                self.last_leg = knee
            self.knee_up[knee] = up
        recent = [s for s in self.steps if t - s < 1.5]
        f["step_cadence"] = (len(recent) - 1) / (recent[-1] - recent[0]) if len(recent) >= 2 and recent[-1] > recent[0] else 0.0

        # arms. "out" for left arm is +x, for right arm is -x (image is mirrored so this matches the viewer).
        for side, s, e, w, sign in (("left", L.LEFT_SHOULDER, L.LEFT_ELBOW, L.LEFT_WRIST, 1),
                                    ("right", L.RIGHT_SHOULDER, L.RIGHT_ELBOW, L.RIGHT_WRIST, -1)):
            f[f"{side}_arm_raise"] = _raise(xy[s], xy[e])
            f[f"{side}_arm_angle"] = _angle(xy[s], xy[e], xy[w])
            f[f"{side}_wrist_out"] = u(sign * (xy[w, 0] - xy[s, 0]))
            f[f"{side}_wrist_up"] = u(xy[s, 1] - xy[w, 1])
        f["wrists_distance"] = u(np.linalg.norm(xy[L.LEFT_WRIST] - xy[L.RIGHT_WRIST]))
        f["wrist_low"] = u(max(xy[L.LEFT_WRIST, 1], xy[L.RIGHT_WRIST, 1]) - hips[1])

        # posture
        f["lean"] = u(shoulders[0] - hips[0])
        f["head_tilt"] = u(xy[L.NOSE, 0] - shoulders[0])
        return {k: round(v, 3) for k, v in f.items()}

    def _hip_drop(self, hy: float, torso: float) -> float:
        # Baseline tracks the highest (smallest y) hip position; drop is how far below it we are.
        inv = -hy
        base = self.hip_base.update(inv)
        return (base - inv) / torso
