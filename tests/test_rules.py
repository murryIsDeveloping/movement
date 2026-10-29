from src.rules import Pose, Condition, RuleEngine


def make():
    return RuleEngine([
        Pose("arm_right", "e", [Condition("right_arm_raise", ">", 70)]),
        Pose("squat", "2", [Condition("hip_drop", ">", 0.4)]),
        Pose("both", "3", [Condition("left_arm_raise", ">", 150), Condition("right_arm_raise", ">", 150)]),
    ])


def test_inactive_by_default():
    r = make()
    s = r.update({"right_arm_raise": 10, "hip_drop": 0, "left_arm_raise": 10})
    assert r.keys() == set()
    assert s["arm_right"]["active"] is False
    assert s["arm_right"]["conds"] == [False]


def test_single_condition_activates():
    r = make()
    r.update({"right_arm_raise": 80, "hip_drop": 0, "left_arm_raise": 10})
    assert r.keys() == {"e"}


def test_all_conditions_required():
    r = make()
    r.update({"right_arm_raise": 160, "hip_drop": 0, "left_arm_raise": 10})
    assert r.keys() == {"e"}
    r.update({"right_arm_raise": 160, "hip_drop": 0, "left_arm_raise": 160})
    assert r.keys() == {"e", "3"}


def test_hysteresis_default_margin():
    r = make()
    r.update({"right_arm_raise": 80, "hip_drop": 0, "left_arm_raise": 10})
    r.update({"right_arm_raise": 66, "hip_drop": 0, "left_arm_raise": 10})  # within 10% margin
    assert r.keys() == {"e"}
    r.update({"right_arm_raise": 50, "hip_drop": 0, "left_arm_raise": 10})
    assert r.keys() == set()


def test_less_than_operator():
    r = RuleEngine([Pose("low", "f", [Condition("wrist_low", "<", 0.5)])])
    r.update({"wrist_low": 0.3}); assert r.keys() == {"f"}
    r.update({"wrist_low": 0.53}); assert r.keys() == {"f"}
    r.update({"wrist_low": 0.7}); assert r.keys() == set()


def test_missing_feature_is_false():
    r = make()
    r.update({})
    assert r.keys() == set()


def test_roundtrip_dict():
    p = Pose("x", "q", [Condition("lean", "<", -0.3)], margin=0.2)
    assert Pose.from_dict(p.to_dict()) == p
