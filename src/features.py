"""Per-frame body measurements. All lengths in torso units, angles in degrees."""
import math
from collections import deque

import numpy as np

from src.landmarks import L, seen

# name -> (description, unit) shown in the GUI
FEATURES = {
    "hip_rise":         ("Hips above standing height, risen within the last 0.4s (jump)", "torso"),
    "hip_drop":         ("Hips below standing height (squat)", "torso"),
    "left_knee_lift":   ("Left knee raised from standing", "torso"),
    "right_knee_lift":  ("Right knee raised from standing", "torso"),
    "left_knee_angle":  ("Left knee angle (hip-knee-ankle): 180 straight. A knee bending out to the side shows; towards the camera barely does. Blank while the ankle is out of frame", "deg"),
    "right_knee_angle": ("Right knee angle (hip-knee-ankle): 180 straight. A knee bending out to the side shows; towards the camera barely does. Blank while the ankle is out of frame", "deg"),
    "left_knee_out":    ("Left knee sideways from the hip (+ = away from body)", "torso"),
    "right_knee_out":   ("Right knee sideways from the hip (+ = away from body)", "torso"),
    "step_cadence":     ("Alternating knee lifts per second (jog)", "steps/s"),
    "left_arm_raise":   ("Left upper arm from hanging: 0 down, 90 out, 180 up", "deg"),
    "right_arm_raise":  ("Right upper arm from hanging: 0 down, 90 out, 180 up", "deg"),
    "left_arm_angle":   ("Left elbow angle: 180 straight", "deg"),
    "right_arm_angle":  ("Right elbow angle: 180 straight", "deg"),
    "left_wrist_out":   ("Left wrist sideways from shoulder (+ = away from body)", "torso"),
    "right_wrist_out":  ("Right wrist sideways from shoulder (+ = away from body)", "torso"),
    "left_wrist_up":    ("Left wrist above shoulder", "torso"),
    "right_wrist_up":   ("Right wrist above shoulder", "torso"),
    "left_wrist_vx":    ("Left hand sideways speed (+ = moving right in the preview; swipe)", "torso/s"),
    "right_wrist_vx":   ("Right hand sideways speed (+ = moving right in the preview; swipe)", "torso/s"),
    "left_wrist_vy":    ("Left hand vertical speed (+ = moving up)", "torso/s"),
    "right_wrist_vy":   ("Right hand vertical speed (+ = moving up)", "torso/s"),
    "left_punch":       ("Left elbow straightening speed (punch sideways/across; straight at camera barely shows)", "deg/s"),
    "right_punch":      ("Right elbow straightening speed (punch sideways/across; straight at camera barely shows)", "deg/s"),
    "clap":             ("Hands closing speed (+ = coming together); add wrists_distance < 0.3 for a clap", "torso/s"),
    "wrists_distance":  ("Distance between wrists", "torso"),
    "wrist_low":        ("Lowest wrist below hips (touch ground)", "torso"),
    "lean":             ("Shoulders sideways of hips (+ = your right... mirrored view)", "torso"),
    "head_tilt":        ("Nose sideways of shoulder centre", "torso"),
}

# unit -> (min, max, step) for the GUI's sliders, meters and stick-figure solver
UNIT_RANGES = {"deg": (0, 180, 1), "torso": (-2, 2, 0.01), "steps/s": (0, 5, 0.1), "torso/s": (-8, 8, 0.1), "deg/s": (-1500, 1500, 10)}
# unit -> what the GUI prints after a value: 92°, 0.31 t (t = torso lengths), 1.80/s. Short: it sits in narrow columns.
UNIT_SYMBOLS = {"deg": "°", "torso": "t", "steps/s": "/s", "torso/s": "t/s", "deg/s": "°/s"}

# what the GUI knows about each feature
FEATURE_INFO = {k: {"desc": d, "unit": u, "sym": UNIT_SYMBOLS[u], "range": UNIT_RANGES[u]} for k, (d, u) in FEATURES.items()}


MIN_STEP_GAP = 0.15   # seconds; real jogging is ~0.3s a step
STILL_HIPS = 0.05     # torso; hips moving less than this over rise_window count as still
CROUCHED = 0.25       # torso below standing height: a squat, not a posture shift

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

    def update(self, x: float, rate: float | None = None) -> float:
        if self.v is None or x > self.v:
            self.v = x
        else:
            self.v += (x - self.v) * (self.rate if rate is None else rate)
        return self.v


class FeatureEngine:
    def __init__(self, rise_window=0.4, vel_window=0.15):
        self.rise_window = rise_window
        self.vel_window = vel_window
        self.hip_hist: deque[tuple[float, float]] = deque()
        self.vel_hist: deque[tuple[float, dict]] = deque()
        self.knee_up = {L.LEFT_KNEE: False, L.RIGHT_KNEE: False}
        self.last_leg = None
        self.steps: deque[float] = deque(maxlen=6)
        self.reset_baselines()

    def reset_baselines(self):
        self.hip_base = _Baseline()
        self.knee_base = {L.LEFT_KNEE: _Baseline(), L.RIGHT_KNEE: _Baseline()}

    def update(self, p: np.ndarray, t: float) -> dict[str, float]:
        # The GUI's stick figure re-implements the static formulas below (figFeatures in static/figure.js).
        # Change one, change both.
        xy = p[:, :2]
        ls, rs = xy[L.LEFT_SHOULDER], xy[L.RIGHT_SHOULDER]
        lh, rh = xy[L.LEFT_HIP], xy[L.RIGHT_HIP]
        shoulders, hips = (ls + rs) / 2, (lh + rh) / 2
        torso = float(np.linalg.norm(shoulders - hips)) or 1e-6
        u = lambda v: float(v) / torso

        f: dict[str, float] = {}

        # vertical hip motion, against standing height. Standing height only updates while the hips are still,
        # so a jump's peak doesn't become the new "standing" (which made standing after it read as a squat), and
        # standing up out of a squat only gets back to standing height, so it isn't a jump.
        hy = float(hips[1])
        self.hip_hist.append((t, hy))
        while self.hip_hist and t - self.hip_hist[0][0] > self.rise_window:
            self.hip_hist.popleft()
        # Drifting down follows small camera or posture shifts; it crawls in a held squat so the squat doesn't
        # fade and standing up from it doesn't rise above a sunken baseline.
        ys = [h[1] for h in self.hip_hist]
        if self.hip_base.v is None or u(max(ys) - min(ys)) < STILL_HIPS:
            crouched = self.hip_base.v is not None and u(hy + self.hip_base.v) > CROUCHED
            self.hip_base.update(-hy, 0.001 if crouched else None)   # y is down: the baseline tracks the highest hips
        stand = -self.hip_base.v
        # a jump is above standing height AND a fast rise: walking back from the camera creeps above a baseline
        # that can't update while moving, but slowly
        f["hip_rise"] = max(0.0, min(u(stand - hy), u(max(ys) - hy)))
        f["hip_drop"] = max(0.0, u(hy - stand))

        # knees. Mirrored, like the arms below: "out" is -x for the left knee and +x for the right.
        for side, knee, hip, ankle, sign in (("left", L.LEFT_KNEE, L.LEFT_HIP, L.LEFT_ANKLE, -1),
                                             ("right", L.RIGHT_KNEE, L.RIGHT_HIP, L.RIGHT_ANKLE, 1)):
            f[f"{side}_knee_out"] = u(sign * (xy[knee, 0] - xy[hip, 0]))
            if seen(p, ankle):   # a guessed ankle off the bottom edge reads as a straight leg
                f[f"{side}_knee_angle"] = _angle(xy[hip], xy[knee], xy[ankle])
            rel = float(xy[knee, 1] - xy[hip, 1])
            base = self.knee_base[knee].update(rel)
            lift = u(base - rel)
            f[f"{side}_knee_lift"] = lift
            up = lift > 0.15
            # a squat lifts both knees a few hundredths of a second apart: too quick to be a step
            quick = bool(self.steps) and t - self.steps[-1] < MIN_STEP_GAP
            if up and not self.knee_up[knee] and self.last_leg != knee and not quick:
                self.steps.append(t)
                self.last_leg = knee
            self.knee_up[knee] = up
        recent = [s for s in self.steps if t - s < 1.5]
        f["step_cadence"] = (len(recent) - 1) / (recent[-1] - recent[0]) if len(recent) >= 2 and recent[-1] > recent[0] else 0.0

        # arms. Mirrored image, like a mirror: the user's left is on the image left, so "out" is -x for the
        # left arm and +x for the right.
        for side, s, e, w, sign in (("left", L.LEFT_SHOULDER, L.LEFT_ELBOW, L.LEFT_WRIST, -1),
                                    ("right", L.RIGHT_SHOULDER, L.RIGHT_ELBOW, L.RIGHT_WRIST, 1)):
            f[f"{side}_arm_raise"] = _raise(xy[s], xy[e])
            f[f"{side}_arm_angle"] = _angle(xy[s], xy[e], xy[w])
            f[f"{side}_wrist_out"] = u(sign * (xy[w, 0] - xy[s, 0]))
            f[f"{side}_wrist_up"] = u(xy[s, 1] - xy[w, 1])
        f["wrists_distance"] = u(np.linalg.norm(xy[L.LEFT_WRIST] - xy[L.RIGHT_WRIST]))

        # speeds over the last vel_window seconds: long enough to smooth jitter, short enough for a swipe or punch
        now = {"left": xy[L.LEFT_WRIST].copy(), "right": xy[L.RIGHT_WRIST].copy(),
               "left_angle": f["left_arm_angle"], "right_angle": f["right_arm_angle"], "dist": f["wrists_distance"]}
        self.vel_hist.append((t, now))
        while t - self.vel_hist[0][0] > self.vel_window:
            self.vel_hist.popleft()
        t0, then = self.vel_hist[0]
        dt = t - t0
        rate = (lambda a, b: (a - b) / dt) if dt > 0.03 else (lambda a, b: a * 0)
        for side in ("left", "right"):
            v = rate(now[side], then[side])
            f[f"{side}_wrist_vx"] = u(v[0])
            f[f"{side}_wrist_vy"] = u(-v[1])
            f[f"{side}_punch"] = rate(now[f"{side}_angle"], then[f"{side}_angle"])
        f["clap"] = rate(then["dist"], now["dist"])
        f["wrist_low"] = u(max(xy[L.LEFT_WRIST, 1], xy[L.RIGHT_WRIST, 1]) - hips[1])

        # posture
        f["lean"] = u(shoulders[0] - hips[0])
        f["head_tilt"] = u(xy[L.NOSE, 0] - shoulders[0])
        return {k: round(v, 3) for k, v in f.items()}
