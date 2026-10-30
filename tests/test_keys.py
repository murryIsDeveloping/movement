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


def test_release_all():
    kb = FakeKB()
    ks = KeyState(kb)
    ks.apply({"w", "q"})
    ks.release_all()
    assert sorted(kb.log[2:]) == [("up", "q"), ("up", "w")]


class BadKB(FakeKB):
    """pynput raises on a name it doesn't know."""
    def press(self, k):
        if k == "spac":
            raise ValueError(k)
        super().press(k)


def test_apply_survives_a_key_the_backend_rejects(capsys):
    kb = BadKB()
    ks = KeyState(kb)
    ks.apply({"spac", "w"})
    ks.apply({"spac", "w"})
    assert kb.log == [("down", "w")] and ks.held == {"w"}
    assert capsys.readouterr().out.count("'spac' failed") == 1   # logged once, not every frame
    ks.release_all()
    assert kb.log[-1] == ("up", "w") and ks.held == set()
