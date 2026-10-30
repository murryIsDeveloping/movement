import math
import re
from pathlib import Path

import numpy as np

from src.features import FEATURE_INFO, FEATURES, UNIT_RANGES, FeatureEngine
from src.landmarks import L
from tests.fixtures import standing


def run(engine, frames):
    out = None
    for t, p in frames:
        out = engine.update(p, t)
    return out


def still(n=30):
    return [(i / 30, standing()) for i in range(n)]


def test_every_declared_feature_present():
    f = run(FeatureEngine(), still())
    assert set(f) == set(FEATURES)


def test_every_feature_has_a_unit():
    for k, i in FEATURE_INFO.items():
        assert i["desc"] and i["unit"] in UNIT_RANGES and i["sym"], k
    # the GUI's stick figure aims past thresholds by a per-unit margin
    fig = (Path(__file__).parent.parent / "static" / "figure.js").read_text(encoding="utf-8")
    margins = re.search(r"FIG_MARGIN = \{(.*?)\}", fig).group(1)
    assert set(re.findall(r"'?([\w/]+)'?:", margins)) == set(UNIT_RANGES)


def test_standing_baselines_near_zero():
    f = run(FeatureEngine(), still())
    for k in ("hip_rise", "hip_drop", "left_knee_lift", "right_knee_lift", "lean", "step_cadence"):
        assert abs(f[k]) < 0.15, (k, f[k])
    assert f["wrists_distance"] > 1.0


def test_arm_raise_angles():
    p = standing()
    # right arm straight out to side (image right: mirrored, so the right side of the body is at larger x)
    p[L.RIGHT_ELBOW, :2] = p[L.RIGHT_SHOULDER, :2] + (0.1, 0)
    p[L.RIGHT_WRIST, :2] = p[L.RIGHT_SHOULDER, :2] + (0.2, 0)
    # left arm straight up
    p[L.LEFT_ELBOW, :2] = p[L.LEFT_SHOULDER, :2] + (0, -0.1)
    p[L.LEFT_WRIST, :2] = p[L.LEFT_SHOULDER, :2] + (0, -0.2)
    f = FeatureEngine().update(p, 0.0)
    assert math.isclose(f["right_arm_raise"], 90, abs_tol=1)
    assert math.isclose(f["left_arm_raise"], 180, abs_tol=1)
    assert math.isclose(f["right_arm_angle"], 180, abs_tol=1)


def test_arm_angle_bent():
    p = standing()
    p[L.RIGHT_ELBOW, :2] = p[L.RIGHT_SHOULDER, :2] + (0.1, 0)
    p[L.RIGHT_WRIST, :2] = p[L.RIGHT_ELBOW, :2] + (0, -0.1)
    f = FeatureEngine().update(p, 0.0)
    assert math.isclose(f["right_arm_angle"], 90, abs_tol=1)


def test_wrist_out_positive_in_torso_units():
    p = standing()
    p[L.RIGHT_WRIST, :2] = p[L.RIGHT_SHOULDER, :2] + (0.2, 0)
    f = FeatureEngine().update(p, 0.0)
    assert math.isclose(f["right_wrist_out"], 1.0, abs_tol=0.01)
    assert math.isclose(f["right_wrist_up"], 0.0, abs_tol=0.01)


def test_hip_drop_after_squat():
    e = FeatureEngine()
    run(e, still())
    p = standing(); p[[L.LEFT_HIP, L.RIGHT_HIP, L.LEFT_SHOULDER, L.RIGHT_SHOULDER], 1] += 0.1
    f = e.update(p, 1.0)
    assert f["hip_drop"] > 0.4


def test_hip_rise_on_jump():
    e = FeatureEngine()
    run(e, still())
    p = standing(); p[[L.LEFT_HIP, L.RIGHT_HIP], 1] -= 0.06
    f = e.update(p, 1.05)
    assert f["hip_rise"] > 0.25


def hips_at(dy):
    """Standing with the whole upper body shifted by dy (+ = down), like a squat or a jump."""
    p = standing(); p[[L.NOSE, L.LEFT_SHOULDER, L.RIGHT_SHOULDER, L.LEFT_ELBOW, L.RIGHT_ELBOW,
                       L.LEFT_WRIST, L.RIGHT_WRIST, L.LEFT_HIP, L.RIGHT_HIP], 1] += dy
    return p


def test_standing_after_a_jump_is_not_a_squat():
    # the jump's peak used to become "standing height", so landing read as a deep squat
    e = FeatureEngine()
    run(e, still())
    jump = [0.04, 0.0, -0.08, -0.16, -0.2, -0.16, -0.08, 0.0, 0.03, 0.0]   # dip, up, down, absorb
    peak = max(e.update(hips_at(dy), 1.0 + i / 30)["hip_rise"] for i, dy in enumerate(jump))
    assert peak > 0.6
    f = run(e, [(1.4 + i / 30, standing()) for i in range(30)])
    assert f["hip_drop"] < 0.05


def test_standing_up_from_a_squat_is_not_a_jump():
    e = FeatureEngine()
    run(e, still())
    down = [(1.0 + i / 30, hips_at(0.15 * min(i, 10) / 10)) for i in range(150)]   # squat, hold 5s
    assert run(e, down)["hip_drop"] > 0.5
    up = [(6.0 + i / 30, hips_at(0.15 * max(0, 6 - i) / 6)) for i in range(20)]   # stand up quickly
    assert max(e.update(p, t)["hip_rise"] for t, p in up) < 0.1


def test_walking_back_from_the_camera_is_not_a_jump():
    # hips creep up the image over 2s while bobbing with each step, so standing height can't update
    e = FeatureEngine()
    run(e, still())
    walk = [(1.0 + i / 30, hips_at(-0.1 * i / 60 + 0.02 * math.sin(i / 30 * 2 * math.pi * 2))) for i in range(60)]
    assert max(e.update(p, t)["hip_rise"] for t, p in walk) < 0.32


def test_knee_lift():
    e = FeatureEngine()
    run(e, still())
    p = standing(); p[L.LEFT_KNEE, 1] -= 0.1
    f = e.update(p, 1.0)
    assert f["left_knee_lift"] > 0.4
    assert f["right_knee_lift"] < 0.05


def test_step_cadence_when_jogging():
    e = FeatureEngine()
    frames = []
    for i in range(90):
        t = i / 30
        p = standing()
        ph = math.sin(2 * math.pi * t)
        p[L.LEFT_KNEE, 1] -= max(ph, 0) * 0.08
        p[L.RIGHT_KNEE, 1] -= max(-ph, 0) * 0.08
        frames.append((t, p))
    f = run(e, frames)
    assert f["step_cadence"] > 1.5


def test_squat_is_not_a_step():
    # both knees lift two frames apart going down into a squat, which used to read as 16 steps/s
    e = FeatureEngine()
    run(e, still())
    f = None
    for i in range(1, 30):
        p = standing(); t = 1.0 + i / 30
        p[L.LEFT_HIP, 1] += min(i, 6) * 0.025; p[L.RIGHT_HIP, 1] += min(i, 6) * 0.025
        if i < 3:   # right knee lags: it drops with the hip at first, so it reads as not lifted yet
            p[L.RIGHT_KNEE, 1] += min(i, 6) * 0.025
        f = e.update(p, t)
    assert f["step_cadence"] == 0


def test_wrist_velocity_on_swipe():
    e = FeatureEngine()
    run(e, still())
    # right wrist sweeps 0.3 image widths leftwards (1.5 torso) over 0.3s
    f = None
    for i in range(1, 10):
        p = standing(); p[L.RIGHT_WRIST, 0] -= 0.3 * i / 9
        f = e.update(p, 1.0 + 0.3 * i / 9)
    assert f["right_wrist_vx"] < -4
    assert abs(f["left_wrist_vx"]) < 0.1
    assert abs(f["right_wrist_vy"]) < 0.1


def test_motion_features_zero_when_still():
    f = run(FeatureEngine(), still())
    for k in ("left_wrist_vx", "right_wrist_vx", "left_wrist_vy", "right_wrist_vy", "left_punch", "right_punch", "clap"):
        assert f[k] == 0, (k, f[k])


def test_punch_on_fast_elbow_extension():
    e = FeatureEngine()
    f = None
    # right arm out sideways, elbow goes from 90 to straight over 0.15s
    for i in range(14):   # extend over frames 0-5, then hold straight past the speed window
        a = math.radians(90 * (1 - min(i, 5) / 5))   # forearm bend from straight
        p = standing()
        p[L.RIGHT_ELBOW, :2] = p[L.RIGHT_SHOULDER, :2] + (0.1, 0)
        p[L.RIGHT_WRIST, :2] = p[L.RIGHT_ELBOW, :2] + (0.1 * math.cos(a), -0.1 * math.sin(a))
        f = e.update(p, 1.0 + i * 0.03)
        if i == 5:
            assert f["right_punch"] > 400
    assert abs(f["left_punch"]) < 1
    assert abs(f["right_punch"]) < 1   # arm now held straight


def test_clap_when_hands_come_together():
    e = FeatureEngine()
    run(e, still())
    f = None
    for i in range(1, 6):
        p = standing()
        p[L.LEFT_WRIST, :2] = (0.37 + 0.12 * i / 5, 0.35)
        p[L.RIGHT_WRIST, :2] = (0.63 - 0.12 * i / 5, 0.35)
        f = e.update(p, 1.0 + i * 0.03)
    assert f["clap"] > 4
    assert f["wrists_distance"] < 0.15


def test_wrist_out_sign_per_side():
    # mirrored view: each wrist moving away from the body is positive for its own side
    p = standing()
    p[L.LEFT_WRIST, 0] = p[L.LEFT_SHOULDER, 0] - 0.2
    p[L.RIGHT_WRIST, 0] = p[L.RIGHT_SHOULDER, 0] + 0.2
    f = FeatureEngine().update(p, 0.0)
    assert math.isclose(f["left_wrist_out"], 1.0, abs_tol=0.01)
    assert math.isclose(f["right_wrist_out"], 1.0, abs_tol=0.01)


def test_lean_sign():
    p = standing(); p[[L.LEFT_SHOULDER, L.RIGHT_SHOULDER, L.NOSE], 0] += 0.1
    f = FeatureEngine().update(p, 0.0)
    assert f["lean"] > 0.4
    p = standing(); p[[L.LEFT_SHOULDER, L.RIGHT_SHOULDER, L.NOSE], 0] -= 0.1
    assert FeatureEngine().update(p, 0.0)["lean"] < -0.4


def test_wrist_low_when_touching_ground():
    p = standing(); p[L.RIGHT_WRIST, 1] = p[L.RIGHT_ANKLE, 1]
    f = FeatureEngine().update(p, 0.0)
    assert f["wrist_low"] > 1.5


def test_knee_angle_straight_and_bent_out():
    f = FeatureEngine().update(standing(), 0.0)
    assert math.isclose(f["left_knee_angle"], 180, abs_tol=1)
    assert abs(f["left_knee_out"]) < 0.01
    # warrior-style: right knee out to the side over a planted ankle, thigh level
    p = standing()
    p[L.RIGHT_KNEE, :2] = p[L.RIGHT_HIP, :2] + (0.2, 0.0)
    p[L.RIGHT_ANKLE, :2] = p[L.RIGHT_KNEE, :2] + (0.0, 0.2)
    f = FeatureEngine().update(p, 0.0)
    assert math.isclose(f["right_knee_angle"], 90, abs_tol=1)
    assert math.isclose(f["right_knee_out"], 1.0, abs_tol=0.01)   # 0.2 over a torso of 0.2


def test_knee_out_is_away_from_body_on_both_sides():
    p = standing()
    p[L.LEFT_KNEE, 0] -= 0.05    # mirrored: the user's left is at small x
    p[L.RIGHT_KNEE, 0] += 0.05
    f = FeatureEngine().update(p, 0.0)
    assert f["left_knee_out"] > 0.2 and f["right_knee_out"] > 0.2


def test_knee_angle_blank_while_ankle_out_of_frame():
    p = np.hstack([standing(), np.ones((33, 1))])   # with a visibility column
    p[L.LEFT_ANKLE, 1] = 1.05                       # off the bottom edge
    p[L.RIGHT_ANKLE, 3] = 0.1                       # hidden
    f = FeatureEngine().update(p, 0.0)
    assert "left_knee_angle" not in f and "right_knee_angle" not in f
    assert "left_knee_out" in f
