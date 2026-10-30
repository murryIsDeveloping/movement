import asyncio

import yaml
from aiohttp.test_utils import TestClient, TestServer

from src import config, library
from src.server import Hub, make_app


def test_load_creates_default_from_library(tmp_path):
    path = tmp_path / "config.yaml"
    cfg = config.load(path)
    assert path.exists() and {k: v for k, v in cfg.items() if k != "poses"} == {k: v for k, v in config.DEFAULT.items() if k != "poses"}
    lib = library.load(library.BUILTIN, tmp_path / "my_presets.yaml")
    group = next(g for g in lib["groups"] if g["name"] == config.FIRST_RUN_GROUP)
    presets = {p["name"]: p for p in lib["presets"]}
    assert [p["preset"] for p in cfg["poses"]] == [p["name"] for p in cfg["poses"]] == group["presets"]
    assert all(presets[p["preset"]]["status"] == "tested" for p in cfg["poses"])
    assert cfg["poses"] == library.group_poses(config.FIRST_RUN_GROUP)   # the mapping itself is tested in test_library
    assert len(config.poses_lenient(cfg)) == len(group["presets"])


def test_first_run_falls_back_to_basic_poses(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(library, "BUILTIN", tmp_path / "missing.yaml")
    assert config.load(tmp_path / "config.yaml") == config.DEFAULT
    other = tmp_path / "presets.yaml"
    other.write_text(yaml.safe_dump({"presets": [], "groups": [{"name": "renamed", "presets": []}]}))
    monkeypatch.setattr(library, "BUILTIN", other)
    assert config.first_run() == config.DEFAULT
    assert "can't load built-in group 'wow hunter'" in capsys.readouterr().out


def test_existing_config_keeps_its_poses(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"poses": [{"name": "a", "key": "w"}]}))
    assert config.load(path)["poses"] == [{"name": "a", "key": "w"}]


def test_load_merges_nested_defaults(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"camera": {"index": 2}, "port": 9000, "extra": 1}))
    cfg = config.load(path)
    assert cfg["camera"] == {"index": 2, "width": 640, "height": 480}
    assert cfg["port"] == 9000 and cfg["extra"] == 1
    assert cfg["poses"] == config.DEFAULT["poses"]


def test_load_adds_clashes_ok_to_older_configs(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"poses": []}))
    assert config.load(path)["clashes_ok"] == []
    path.write_text(yaml.safe_dump({"poses": [], "clashes_ok": [["star jump", "jump", "same"]]}))
    assert config.load(path)["clashes_ok"] == [["jump", "star jump", "same"]]


def test_clean_clashes_ok_drops_bad_entries():
    assert config.clean_clashes_ok(5) == config.clean_clashes_ok(None) == []
    assert config.clean_clashes_ok([1, "ab", ["a"], ["a", 2], ["b", "a"], ["a", "b", "b-in-a"]]) == [
        ["a", "b", "overlap"], ["a", "b", "b-in-a"]]


def test_load_drops_saved_send_keys(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"send_keys": True, "poses": []}))   # saved by an older build
    assert "send_keys" not in config.load(path) and "send_keys" not in config.DEFAULT


def put_config(body: str):
    async def go():
        hub, got = Hub(), []
        hub.on_config = got.append
        async with TestClient(TestServer(make_app(hub))) as client:
            r = await client.put("/config", data=body)
            return r.status, await r.json(), got
    return asyncio.run(go())


def test_import_accepts_valid_poses():
    status, j, got = put_config(yaml.safe_dump({"poses": config.DEFAULT["poses"]}))
    assert status == 200 and j == {"ok": True, "poses": len(config.DEFAULT["poses"])}
    assert got[0]["poses"] == config.DEFAULT["poses"]


def test_import_never_turns_keys_on():
    status, j, got = put_config(yaml.safe_dump({"send_keys": True, "poses": config.DEFAULT["poses"]}))
    assert status == 200 and "send_keys" not in got[0]


def test_import_rejects_unknown_feature():
    bad = {"poses": [{"name": "x", "key": "q", "conditions": [{"feature": "nope", "op": ">", "value": 1}]}]}
    status, j, got = put_config(yaml.safe_dump(bad))
    assert status == 400 and "unknown feature" in j["error"] and got == []


def test_import_rejects_missing_poses():
    status, j, got = put_config("send_keys: true\n")
    assert status == 400 and got == []


def test_import_rejects_unknown_key():
    status, j, got = put_config(yaml.safe_dump({"poses": [{"name": "jump", "key": "spac"}]}))
    assert status == 400 and "unknown key 'spac'" in j["error"] and got == []


def test_startup_disables_bad_key_and_skips_broken_pose(tmp_path, capsys):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"poses": [{"name": "a", "key": "w"}, {"name": "b", "key": "spa"},
                                              {"name": "c", "key": "x", "conditions": [{"feature": "nope", "op": ">", "value": 1}]}]}))
    cfg = config.load(path)
    poses = config.poses_lenient(cfg)
    assert [(p.name, p.key, p.enabled) for p in poses] == [("a", "w", True), ("b", "1", False)]
    assert [d["name"] for d in cfg["poses"]] == ["a", "b"] and cfg["poses"][1]["key"] == "1"   # an export or the next save matches
    out = capsys.readouterr().out
    assert "unknown key 'spa', pose disabled with key 1" in out and "unknown feature 'nope', pose skipped" in out
