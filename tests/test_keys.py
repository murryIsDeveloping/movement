import re
from pathlib import Path

from src.keys import KEY_NAMES, KeyState, valid_key


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


def test_gui_key_capture_only_produces_valid_names():
    """The GUI's keydown → pynput map (KEY_MAP, SIDED in static/index.html) must only produce names valid_key accepts."""
    html = (Path(__file__).parent.parent / "static" / "index.html").read_text(encoding="utf-8")
    block = lambda name: re.search(r"const %s = \{(.*?)\};" % name, html, re.S).group(1)
    mapped = re.findall(r":\s*'([^']*)'", block("KEY_MAP"))
    sided = [f"{b}_{s}" for b in re.findall(r":\s*'([^']*)'", block("SIDED")) for s in "lr"]
    assert len(mapped) > 20 and len(sided) == 8
    fkeys = [f"f{i}" for i in range(1, 25)]   # /^F([1-9]|1\d|2[0-4])$/ lowercased
    assert [k for k in mapped + sided + fkeys if not (valid_key(k) and k in KEY_NAMES)] == []
