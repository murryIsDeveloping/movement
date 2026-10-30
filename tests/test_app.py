import yaml

import app
from src import config


class FakeKB:
    def __init__(self):
        self.log = []

    def press(self, k): self.log.append(("down", k))
    def release(self, k): self.log.append(("up", k))


def make_app(tmp_path, monkeypatch, cfg):
    """An App on a temp config.yaml with a fake keyboard; the camera only starts in run(), so none is opened."""
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    load, save = config.load, config.save
    monkeypatch.setattr(config, "load", lambda: load(path))
    monkeypatch.setattr(config, "save", lambda c: save(c, path))
    monkeypatch.setattr(app, "pynput_keyboard", FakeKB)
    monkeypatch.setattr(app, "system_mouse", FakeMouse)
    return app.App(), path


class FakeMouse:
    def __init__(self):
        self.log = []

    def press(self, b): self.log.append(("down", b))
    def release(self, b): self.log.append(("up", b))
    def move(self, dx, dy): self.log.append((dx, dy))


def test_send_keys_starts_off_and_is_never_saved(tmp_path, monkeypatch):
    a, path = make_app(tmp_path, monkeypatch, {"send_keys": True, "poses": [{"name": "jump", "key": "space"}]})
    assert a.send_keys is False and "send_keys" not in a.cfg and "send_keys" not in a.hub.get_config()
    a.set_config({"poses": a.cfg["poses"], "send_keys": True})
    assert a.send_keys is True
    on_disk = yaml.safe_load(path.read_text())
    assert "send_keys" not in on_disk and on_disk["poses"] == [{"name": "jump", "key": "space"}]   # stale key dropped too
    assert "send_keys" not in a.cfg and "send_keys" not in a.hub.get_config()
    a.set_config({"poses": a.cfg["poses"]})   # an edit without send_keys (an import) leaves the session state alone
    assert a.send_keys is True


def test_send_keys_off_releases_held_keys(tmp_path, monkeypatch):
    a, _ = make_app(tmp_path, monkeypatch, {"poses": []})
    a.set_config({"send_keys": True})
    a.keys.apply({"w"})
    a.set_config({"send_keys": False})
    assert a.send_keys is False and a.keys.kb.log == [("down", "w"), ("up", "w")]


def test_send_keys_off_or_camera_mode_off_lets_go_of_the_drag(tmp_path, monkeypatch):
    a, path = make_app(tmp_path, monkeypatch, {"poses": []})
    a.set_config({"send_keys": True, "look": {"enabled": True}})
    assert a.cfg["look"]["clap"] == 3.0 and yaml.safe_load(path.read_text())["look"]["enabled"] is True   # merged, saved
    a.look.on = True
    a.mouse.apply(True, "right", (0.0, 0.0), 0.03)
    a.set_config({"send_keys": False})
    assert a.mouse.mouse.log == [("down", "right"), ("up", "right")] and a.look.on   # still in camera mode, just not dragging
    a.set_config({"look": {"enabled": False}})
    assert not a.look.on
