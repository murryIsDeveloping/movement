from itertools import count

import pytest

from src.rules import Pose, Condition, RuleEngine

_clock = count(step=0.05)


def tick() -> float:
    """Next frame time: rule updates need time moving forward, like the camera loop."""
    return next(_clock)


def make():
    return RuleEngine([
        Pose("arm_right", "e", [Condition("right_arm_raise", ">", 70)]),
        Pose("squat", "2", [Condition("hip_drop", ">", 0.4)]),
        Pose("both", "3", [Condition("left_arm_raise", ">", 150), Condition("right_arm_raise", ">", 150)]),
    ])


def test_inactive_by_default():
    r = make()
    s = r.update({"right_arm_raise": 10, "hip_drop": 0, "left_arm_raise": 10}, tick())
    assert r.keys() == set()
    assert s[0]["active"] is False
    assert s[0]["conds"] == [False]


def test_single_condition_activates():
    r = make()
    r.update({"right_arm_raise": 80, "hip_drop": 0, "left_arm_raise": 10}, tick())
    assert r.keys() == {"e"}


def test_all_conditions_required():
    r = make()
    r.update({"right_arm_raise": 160, "hip_drop": 0, "left_arm_raise": 10}, tick())
    assert r.keys() == {"e"}
    r.update({"right_arm_raise": 160, "hip_drop": 0, "left_arm_raise": 160}, tick())
    assert r.keys() == {"e", "3"}


def test_hysteresis_default_margin():
    r = make()
    r.update({"right_arm_raise": 80, "hip_drop": 0, "left_arm_raise": 10}, tick())
    r.update({"right_arm_raise": 66, "hip_drop": 0, "left_arm_raise": 10}, tick())  # within 10% margin
    assert r.keys() == {"e"}
    r.update({"right_arm_raise": 50, "hip_drop": 0, "left_arm_raise": 10}, tick())
    assert r.keys() == set()


def test_less_than_operator():
    r = RuleEngine([Pose("low", "f", [Condition("wrist_low", "<", 0.5)])])
    r.update({"wrist_low": 0.3}, tick()); assert r.keys() == {"f"}
    r.update({"wrist_low": 0.53}, tick()); assert r.keys() == {"f"}
    r.update({"wrist_low": 0.7}, tick()); assert r.keys() == set()


def test_missing_feature_is_false():
    r = make()
    r.update({}, tick())
    assert r.keys() == set()


def test_roundtrip_dict():
    p = Pose("x", "q", [Condition("lean", "<", -0.3)], margin=0.2)
    assert Pose.from_dict(p.to_dict()) == p


def test_same_name_poses_keep_separate_state():
    r = RuleEngine([Pose("p", "a", [Condition("lean", ">", 0.2)]), Pose("p", "d", [Condition("lean", "<", -0.2)])])
    s = r.update({"lean": 0.5}, tick())
    assert r.keys() == {"a"}
    assert [x["active"] for x in s] == [True, False]


def test_from_dict_rejects_unknown_feature():
    with pytest.raises(ValueError, match="unknown feature"):
        Pose.from_dict({"name": "x", "key": "q", "conditions": [{"feature": "arm_rasie", "op": ">", "value": 1}]})


def test_from_dict_rejects_bad_op():
    with pytest.raises(ValueError, match="op must be"):
        Pose.from_dict({"name": "x", "key": "q", "conditions": [{"feature": "lean", "op": ">=", "value": 1}]})


@pytest.mark.parametrize("key", ["spac", "", "Space", "f99"])
def test_from_dict_rejects_unknown_key(key):
    with pytest.raises(ValueError, match=f"unknown key {key!r}"):
        Pose.from_dict({"name": "x", "key": key, "conditions": [{"feature": "lean", "op": ">", "value": 1}]})


@pytest.mark.parametrize("key", ["q", "1", 1, "-", "space", "shift_l", "f12"])
def test_from_dict_accepts_char_or_key_name(key):
    assert Pose.from_dict({"name": "x", "key": key}).key == str(key)


def test_hold_keeps_key_down_after_a_one_frame_pose():
    r = RuleEngine([Pose("punch", "n", [Condition("right_punch", ">", 500)], hold=0.3)])
    r.update({"right_punch": 800}, 10.0)
    r.update({"right_punch": 0}, 10.2)
    assert r.keys() == {"n"}
    r.update({"right_punch": 0}, 10.35)
    assert r.keys() == set()


def test_hold_bridges_a_brief_dropout():
    r = RuleEngine([Pose("right", "d", [Condition("lean", "<", 0.1)], hold=0.2)])
    r.update({"lean": 0.0}, 1.0)
    r.update({"lean": 0.5}, 1.1)        # flicker
    r.update({"lean": 0.0}, 1.15)
    r.update({"lean": 0.5}, 1.3)
    assert r.keys() == {"d"}            # hold restarted at 1.15
    r.update({"lean": 0.5}, 1.4)
    assert r.keys() == set()


def test_delay_ignores_an_arm_passing_through():
    r = RuleEngine([Pose("right", "d", [Condition("right_arm_raise", ">", 76)], delay=0.3)])
    r.update({"right_arm_raise": 90}, 1.0)
    r.update({"right_arm_raise": 90}, 1.2)
    assert r.keys() == set()
    r.update({"right_arm_raise": 20}, 1.25)    # dropped before 0.3s: the next try counts from scratch
    r.update({"right_arm_raise": 90}, 1.4)
    r.update({"right_arm_raise": 90}, 1.6)
    assert r.keys() == set()


def test_delay_fires_once_held_and_stays_without_restarting():
    r = RuleEngine([Pose("right", "d", [Condition("right_arm_raise", ">", 76)], delay=0.3)])
    r.update({"right_arm_raise": 90}, 1.0)
    r.update({"right_arm_raise": 90}, 1.3)
    assert r.keys() == {"d"}
    r.update({"right_arm_raise": 90}, 1.35)
    assert r.keys() == {"d"}
    r.update({"right_arm_raise": 20}, 1.4)
    assert r.keys() == set()


def test_roundtrip_dict_with_delay():
    p = Pose("x", "q", [Condition("lean", "<", -0.3)], hold=0.2, delay=0.35)
    assert Pose.from_dict(p.to_dict()) == p


def test_release_drops_held_keys_at_once():
    r = RuleEngine([Pose("punch", "n", [Condition("right_punch", ">", 500)], hold=0.4)])
    r.update({"right_punch": 800}, 1.0)
    r.release()
    r.update({}, 1.05)
    assert r.keys() == set()


def test_no_hold_releases_next_frame():
    r = RuleEngine([Pose("p", "a", [Condition("lean", ">", 0.2)])])
    r.update({"lean": 0.5}, 1.0)
    r.update({"lean": 0.0}, 1.03)
    assert r.keys() == set()
