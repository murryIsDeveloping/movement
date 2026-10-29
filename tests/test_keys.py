from src.keys import KeyState


class FakeKB:
    def __init__(self):
        self.log = []

    def press(self, k): self.log.append(("down", k))
    def release(self, k): self.log.append(("up", k))


def test_press_on_enter_release_on_exit():
    kb = FakeKB()
    ks = KeyState(kb)
    ks.apply({"w"})
    ks.apply({"w"})
    ks.apply(set())
    assert kb.log == [("down", "w"), ("up", "w")]


def test_pulse_taps_once():
    kb = FakeKB()
    ks = KeyState(kb)
    ks.pulse("space")
    assert kb.log == [("down", "space"), ("up", "space")]


def test_release_all():
    kb = FakeKB()
    ks = KeyState(kb)
    ks.apply({"w", "q"})
    ks.release_all()
    assert sorted(kb.log[2:]) == [("up", "q"), ("up", "w")]
