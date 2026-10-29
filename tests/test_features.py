import math

import numpy as np

from src.features import FEATURES, FeatureEngine
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
