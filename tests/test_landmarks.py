import numpy as np

from src.landmarks import FrameWatch, L, out_of_frame
from tests.fixtures import standing


def with_visibility(p, v=0.99):
    return np.hstack([p, np.full((len(p), 1), v)])


def test_whole_body_in_frame():
    assert out_of_frame(with_visibility(standing())) == []


def test_joint_past_the_edge_is_out():
    p = with_visibility(standing()); p[L.LEFT_KNEE, 1] = 1.08    # walked up close: knees below the bottom edge
    assert out_of_frame(p) == ["left knee"]


def test_hidden_joint_is_out():
    p = with_visibility(standing()); p[L.RIGHT_WRIST, 3] = 0.1
    assert out_of_frame(p) == ["right wrist"]


def test_feet_may_be_cut_off():
    p = with_visibility(standing()); p[[L.LEFT_ANKLE, L.RIGHT_ANKLE], 1] = 1.2
    assert out_of_frame(p) == []


def test_blip_out_of_frame_does_not_pause():
    w = FrameWatch(after=0.5)
    inside = with_visibility(standing())
    head_out = inside.copy(); head_out[L.NOSE, 1] = -0.05    # jumped: head over the top edge
    assert w.update(inside, 1.0) == (False, [])
    assert w.update(head_out, 1.1) == (False, ["nose"])
    assert w.update(head_out, 1.4)[0] is False
    assert w.update(inside, 1.5) == (False, [])
    assert w.update(head_out, 1.8)[0] is False               # the clock restarted when back in frame


def test_staying_out_of_frame_pauses():
    w = FrameWatch(after=0.5)
    knees_out = with_visibility(standing()); knees_out[[L.LEFT_KNEE, L.RIGHT_KNEE], 1] = 1.1
    w.update(knees_out, 1.0)
    assert w.update(knees_out, 1.4)[0] is False
    assert w.update(knees_out, 1.5) == (True, ["left knee", "right knee"])


def test_losing_the_body_pauses_after_the_same_wait():
    w = FrameWatch(after=0.5)
    w.update(None, 1.0)
    assert w.update(None, 1.3) == (False, [])
    assert w.update(None, 1.6) == (True, [])


def test_resumed_only_on_the_frame_a_pause_ends():
    w = FrameWatch(after=0.5)
    inside = with_visibility(standing())
    w.update(None, 1.0)
    w.update(None, 1.6)
    assert w.paused and not w.resumed
    w.update(inside, 1.7)
    assert w.resumed and not w.paused
    w.update(inside, 1.8)
    assert not w.resumed
