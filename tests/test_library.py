import asyncio

import pytest
import yaml
from aiohttp.test_utils import TestClient, TestServer

from src import library, server
from src.rules import Pose
from src.server import Hub, make_app

ARM = {"key": "e", "conditions": [{"feature": "right_arm_raise", "op": ">", "value": 70}]}


def preset(name, **kw):
    return {"name": name, **ARM, **kw}


@pytest.fixture
def files(tmp_path):
    b, u = tmp_path / "presets.yaml", tmp_path / "my_presets.yaml"
    b.write_text(yaml.safe_dump({"presets": [preset("arm", status="tested")], "groups": [{"name": "g", "presets": ["arm"]}]}))
    return b, u


def test_shipped_presets_are_valid():
    lib = library.load(library.BUILTIN, library.BUILTIN.parent / "no-such-file.yaml")
    assert len(lib["presets"]) >= 40 and all(p["builtin"] for p in lib["presets"])
    assert sum(p["status"] == "untested" for p in lib["presets"]) >= 20
    for p in lib["presets"]:
        Pose.from_dict(p)


def test_load_flags_builtins(files):
    b, u = files
    u.write_text(yaml.safe_dump({"presets": [preset("mine")], "groups": [{"name": "my g", "presets": ["arm", "mine"]}]}))
    lib = library.load(b, u)
    assert [(p["name"], p["builtin"]) for p in lib["presets"]] == [("arm", True), ("mine", False)]
    assert [(g["name"], g["builtin"]) for g in lib["groups"]] == [("g", True), ("my g", False)]


def test_validate_fills_defaults_and_drops_pose_link():
    p = library.validate({"presets": [preset("arm", preset="old")]})["presets"][0]
    assert p["status"] == "untested" and p["notes"] == "" and p["hold"] == 0.0 and p["builtin"] is False
    assert "preset" not in p


def test_group_poses_maps_like_pose_from_preset(tmp_path):
    b = tmp_path / "presets.yaml"
    b.write_text(yaml.safe_dump({"presets": [preset("arm", hold=0.3), preset("leg", key="x")],
                                 "groups": [{"name": "g", "presets": ["arm", "leg"], "keys": {"arm": "1"}}]}))
    arm, leg = library.group_poses("g", b)
    assert arm == {"name": "arm", "key": "1", "conditions": ARM["conditions"], "margin": 0.1, "enabled": True,
                   "hold": 0.3, "delay": 0.0, "preset": "arm"}
    assert leg["key"] == "x" and leg["preset"] == "leg"
    with pytest.raises(KeyError):
        library.group_poses("nope", b)


def test_user_cannot_change_builtins(files):
    b, u = files
    lib = library.load(b, u)
    lib["presets"][0]["status"] = "untested"
    lib["presets"][0]["conditions"] = []
    lib["presets"].append(preset("mine"))
    lib["groups"].pop(0)   # deleting a built-in group
    saved = library.save(lib, edit_builtins=False, builtin=b, user=u)
    assert saved["presets"][0]["status"] == "tested" and saved["presets"][0]["conditions"]
    assert [g["name"] for g in saved["groups"]] == ["g"]
    assert yaml.safe_load(b.read_text())["presets"][0]["status"] == "tested"
    assert [p["name"] for p in yaml.safe_load(u.read_text())["presets"]] == ["mine"]


def test_user_preset_cannot_take_builtin_name(files):
    b, u = files
    lib = library.load(b, u)
    lib["presets"].append(preset("arm"))   # same name, flagged as the user's
    with pytest.raises(ValueError, match="two presets"):
        library.save(lib, edit_builtins=False, builtin=b, user=u)


def test_running_from_source_edits_builtins(files):
    b, u = files
    lib = library.load(b, u)
    lib["presets"][0]["status"] = "untested"
    library.save(lib, edit_builtins=True, builtin=b, user=u)
    stored = yaml.safe_load(b.read_text())
    assert stored["presets"][0]["status"] == "untested" and "builtin" not in stored["presets"][0]


def test_load_survives_builtins_changing_under_user_file(files):
    b, u = files
    u.write_text(yaml.safe_dump({"presets": [preset("arm"), preset("x")],
                                 "groups": [{"name": "g", "presets": ["arm", "gone"]}, {"name": "mine", "presets": ["arm", "x", "gone"]}]}))
    lib = library.load(b, u)
    assert [p["name"] for p in lib["presets"]] == ["arm", "arm (mine)", "x"]
    groups = {g["name"]: g["presets"] for g in lib["groups"]}
    assert groups["g (mine)"] == ["arm (mine)"] and groups["mine"] == ["arm (mine)", "x"]


@pytest.mark.parametrize("lib, error", [
    ({"presets": [preset("a"), preset("a")]}, "two presets"),
    ({"presets": [preset("a", status="maybe")]}, "status"),
    ({"presets": [{"name": "a", "key": "e", "conditions": [{"feature": "nope", "op": ">", "value": 1}]}]}, "unknown feature"),
    ({"presets": [preset("a")], "groups": [{"name": "g", "presets": ["b"]}]}, "no preset named"),
    ({"presets": [], "groups": [{"name": "g"}, {"name": "g"}]}, "two groups"),
    ({"presets": [preset("a")], "groups": [{"name": "g", "presets": ["a"], "builtin": True}]}, "built-in group"),
])
def test_validate_rejects(lib, error):
    with pytest.raises(ValueError, match=error):
        library.validate(lib)


def test_routes_save_user_half_only(files, monkeypatch):
    b, u = files
    monkeypatch.setattr(library, "BUILTIN", b)
    monkeypatch.setattr(library, "USER", u)
    monkeypatch.setattr(server, "DEV", False)

    async def go():
        async with TestClient(TestServer(make_app(Hub()))) as client:
            lib = await (await client.get("/library")).json()
            lib["presets"].append({**preset("mine"), "builtin": False})
            good = await client.put("/library", json=lib)
            bad = await client.put("/library", json={**lib, "presets": lib["presets"] + [preset("mine")]})
            return lib["edit_builtins"], good.status, bad.status, await (await client.get("/library")).json()
    edit, good, bad, got = asyncio.run(go())
    assert edit is False and good == 200 and bad == 400
    assert [p["name"] for p in got["presets"]] == ["arm", "mine"]


def test_group_keys_override_per_member():
    lib = library.validate({"presets": [preset("a"), preset("b")],
                            "groups": [{"name": "mario", "presets": ["a"], "keys": {"a": "right", "b": "x", "c": "z"}}]})
    g = lib["groups"][0]
    assert g["keys"] == {"a": "right"}   # keys for presets outside the group are dropped
    assert g["notes"] == ""


def test_shipped_game_groups_bind_their_own_keys():
    lib = library.load(library.BUILTIN, library.BUILTIN.parent / "no-such-file.yaml")
    groups = {g["name"]: g for g in lib["groups"]}
    assert groups["mario"]["keys"]["jump"] == "x"
    assert groups["wow hunter"]["keys"]["right punch"] != groups["mario"]["keys"]["right punch"]


def test_renamed_user_preset_keeps_its_group_key(files):
    b, u = files
    u.write_text(yaml.safe_dump({"presets": [preset("arm")], "groups": [{"name": "mine", "presets": ["arm"], "keys": {"arm": "z"}}]}))
    g = library.load(b, u)["groups"][1]
    assert g["presets"] == ["arm (mine)"] and g["keys"] == {"arm (mine)": "z"}


def test_pose_keeps_preset_link():
    assert Pose.from_dict({"name": "a", "preset": "arm", **ARM}).to_dict()["preset"] == "arm"
    assert Pose.from_dict({"name": "a", **ARM}).preset == ""


def test_load_repairs_bad_keys(files, capsys):
    b, u = files
    u.write_text(yaml.safe_dump({"presets": [preset("mine", key="spac")],
                                 "groups": [{"name": "my g", "presets": ["arm", "mine"], "keys": {"arm": "spa", "mine": "x"}}]}))
    lib = library.load(b, u)
    assert lib["presets"][1]["key"] == "1"
    assert lib["groups"][1]["keys"] == {"mine": "x"}
    out = capsys.readouterr().out
    assert "unknown key 'spac', reset" in out and "unknown key 'spa' for 'arm', dropped" in out


def test_validate_rejects_bad_group_key():
    with pytest.raises(ValueError, match="group 'g': unknown key 'spac' for 'arm'"):
        library.validate({"presets": [preset("arm")], "groups": [{"name": "g", "presets": ["arm"], "keys": {"arm": "spac"}}]})
