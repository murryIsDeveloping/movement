import math

from src.look import DEFAULT, Look, LookOutput, toggle_pose

CFG = dict(DEFAULT, enabled=True)
CX, CY = CFG["center"]
APART = {"clap": 0.0, "wrists_distance": 1.5}
CLAP = {"clap": 5.0, "wrists_distance": 0.2}


def hand(dx, dy, **f):
    """Right hand at centre + (dx, dy), hands apart."""
    return {**APART, "right_wrist_out": CX + dx, "right_wrist_up": CY + dy, **f}


class FakeMouse:
    def __init__(self, fail=False):
        self.log, self.fail = [], fail

    def press(self, b):
        if self.fail:
            raise RuntimeError("no mouse")
        self.log.append(("down", b))

    def release(self, b): self.log.append(("up", b))
    def move(self, dx, dy): self.log.append((dx, dy))


def test_a_clap_toggles_once_and_the_next_waits_out_the_lockout():
    lk = Look()
    lk.update(CLAP, 0.0, CFG)
    lk.update(CLAP, 0.03, CFG)   # same clap, still closing: no second toggle
    assert lk.on and lk.locked(0.5, CFG)
    lk.update(APART, 0.5, CFG)
    lk.update(CLAP, 0.6, CFG)    # a bounce inside the lockout
    assert lk.on
    lk.update(APART, 1.1, CFG)
    lk.update(CLAP, 1.2, CFG)
    assert not lk.on and lk.locked(1.5, CFG) and not lk.locked(2.3, CFG)


def test_slow_hands_together_dont_toggle():
    lk = Look()
    lk.update({"clap": 1.0, "wrists_distance": 0.2}, 0.0, CFG)
    lk.update({"clap": 5.0, "wrists_distance": 0.8}, 0.1, CFG)   # fast but far apart
    assert not lk.on


def on():
    lk = Look()
    lk.update(CLAP, 0.0, CFG)
    return lk


def test_off_or_in_the_deadzone_the_stick_is_still():
    lk = Look()
    lk.update(hand(0.5, 0), 0.0, CFG)
    assert lk.velocity == (0.0, 0.0)
    lk = on()
    lk.update(hand(0.1, 0), 2.0, CFG)
    assert lk.velocity == (0.0, 0.0)


def test_hand_right_and_up_moves_the_mouse_right_and_up():
    lk = on()
    lk.update(hand(0.3, 0), 2.0, CFG)
    vx, vy = lk.velocity
    assert vx > 0 and vy == 0
    lk.update(hand(0, 0.3), 2.0, CFG)
    assert lk.velocity[1] < 0   # screen y is down
    lk.update(hand(0, 0.3), 2.0, dict(CFG, invert_y=True))
    assert lk.velocity[1] > 0


def test_speed_grows_with_reach_and_tops_out():
    lk = on()
    speeds = []
    for d in (0.2, 0.35, 0.5, 1.0):
        lk.update(hand(d, 0), 2.0, CFG)
        speeds.append(lk.velocity[0])
    assert speeds[0] < speeds[1] < speeds[2] == speeds[3] == CFG["speed"]


def test_hands_close_freeze_the_stick():
    """Clapping to turn it off swings the right hand in: that mustn't drag the camera on the way."""
    lk = on()
    lk.update(hand(-0.4, 0.1, wrists_distance=0.4), 2.0, CFG)
    assert lk.on and lk.velocity == (0.0, 0.0)


def test_stop_turns_it_off():
    lk = on()
    lk.update(hand(0.4, 0), 2.0, CFG)
    lk.stop()
    assert not lk.on and lk.velocity == (0.0, 0.0)


def test_output_holds_the_button_and_carries_fractions():
    m = FakeMouse()
    out = LookOutput(m)
    for _ in range(3):
        out.apply(True, "right", (10.0, -10.0), 0.05)   # half a pixel a frame
    out.release()
    assert m.log == [("down", "right"), (1, -1), ("up", "right")]


def test_output_never_raises_and_retries_the_press():
    out = LookOutput(FakeMouse(fail=True))
    out.apply(True, "right", (100.0, 0.0), 0.1)
    assert not out.down
    out.mouse.fail = False
    out.apply(True, "right", (100.0, 0.0), 0.1)
    assert out.down and out.mouse.log == [("down", "right"), (10, 0)]


def test_a_pose_can_toggle_instead_of_the_clap():
    cfg = dict(CFG, toggle="hands on head")
    lk = Look()
    lk.update(CLAP, 0.0, cfg)   # a clap does nothing now
    assert not lk.on
    lk.update(APART, 0.1, cfg, pose_on=True)
    lk.update(APART, 0.2, cfg, pose_on=True)   # still held: one toggle
    assert lk.on
    lk.update(hand(-0.4, 0, wrists_distance=0.4), 2.0, cfg)   # the clap freeze is only for the clap
    assert lk.velocity[0] < 0
    lk.update(APART, 2.1, cfg, pose_on=False)
    lk.update(APART, 2.2, cfg, pose_on=True)
    assert not lk.on


def test_toggle_pose_is_the_first_enabled_pose_with_that_name():
    from src.rules import Pose
    poses = [Pose("a", "1", enabled=False), Pose("b", "2"), Pose("a", "3"), Pose("a", "4")]
    on = dict(CFG, toggle="a")
    assert toggle_pose(poses, on) == 2
    assert toggle_pose(poses, dict(on, enabled=False)) is None
    assert toggle_pose(poses, dict(on, toggle="clap")) is None
    assert toggle_pose(poses, dict(on, toggle="gone")) is None


def test_output_swaps_buttons_when_the_setting_changes():
    m = FakeMouse()
    out = LookOutput(m)
    out.apply(True, "right", (0.0, 0.0), 0.03)
    out.apply(True, "left", (0.0, 0.0), 0.03)
    out.release()
    assert m.log == [("down", "right"), ("up", "right"), ("down", "left"), ("up", "left")]


def test_output_can_move_without_a_button():
    m = FakeMouse()
    out = LookOutput(m)
    out.apply(True, None, (100.0, 0.0), 0.1)
    out.apply(False, None, (100.0, 0.0), 0.1)
    assert m.log == [(10, 0)]


def test_a_failed_press_doesnt_sweep_the_pointer():
    out = LookOutput(FakeMouse(fail=True))
    out.apply(True, "right", (100.0, 0.0), 0.1)
    assert out.mouse.log == []
