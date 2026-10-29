import asyncio

import yaml
from aiohttp.test_utils import TestClient, TestServer

from src import config
from src.server import Hub, make_app


def test_load_creates_default(tmp_path):
    path = tmp_path / "config.yaml"
    assert config.load(path) == config.DEFAULT
    assert path.exists()


def test_load_merges_nested_defaults(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump({"camera": {"index": 2}, "port": 9000, "extra": 1}))
    cfg = config.load(path)
    assert cfg["camera"] == {"index": 2, "width": 640, "height": 480}
    assert cfg["port"] == 9000 and cfg["extra"] == 1
    assert cfg["poses"] == config.DEFAULT["poses"]


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


def test_import_rejects_unknown_feature():
    bad = {"poses": [{"name": "x", "key": "q", "conditions": [{"feature": "nope", "op": ">", "value": 1}]}]}
    status, j, got = put_config(yaml.safe_dump(bad))
    assert status == 400 and "unknown feature" in j["error"] and got == []


def test_import_rejects_missing_poses():
    status, j, got = put_config("send_keys: true\n")
    assert status == 400 and got == []
