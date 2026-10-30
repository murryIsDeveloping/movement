import asyncio
import json

from aiohttp.test_utils import TestClient, TestServer

from src import server
from src.rules import Pose
from src.server import Hub, make_app


def routes(app):
    return {(r.method, r.resource.canonical) for r in app.router.routes()}


def test_recording_only_when_running_from_source(monkeypatch):
    monkeypatch.setattr(server, "DEV", True)
    assert ("POST", "/recording") in routes(make_app(Hub()))
    monkeypatch.setattr(server, "DEV", False)   # packaged app: drills aren't recorded
    assert ("POST", "/recording") not in routes(make_app(Hub()))


def test_packaged_app_batches_no_frames(monkeypatch):
    monkeypatch.setattr(server, "DEV", False)
    hub = Hub()
    hub.publish(None, {"t": 1.0, "body": True, "paused": False, "missing": [], "features": {}, "state": []})
    assert '"frames": []' in hub.take()


def ws_config(hub, config):
    """Sends a config edit over the websocket; returns the first non-broadcast reply, or None."""
    async def run():
        async with TestClient(TestServer(make_app(hub))) as client:
            ws = await client.ws_connect("/ws")
            await ws.send_str(json.dumps({"type": "config", "config": config}))
            for _ in range(10):   # broadcasts (state, no type) arrive too, 15 a second
                m = json.loads((await ws.receive(timeout=2)).data)
                if "type" in m:
                    return m
    return asyncio.run(run())


def test_rejected_config_is_sent_back():
    hub, got = Hub(), []
    def on_config(c):
        Pose.from_dict(c["poses"][0])   # what App.set_config does first
        got.append(c)
    hub.on_config = on_config
    bad = {"poses": [{"name": "jab", "key": "spcae", "conditions": []}]}
    assert ws_config(hub, bad) == {"type": "error", "error": "pose 'jab': unknown key 'spcae'"}
    assert ws_config(hub, {"poses": [{"name": "jab", "key": "space"}]}) is None and len(got) == 1


def test_static_files_are_revalidated():
    # a reload rechecks the page but not its scripts: an updated drill.js kept running the old code
    async def run():
        async with TestClient(TestServer(make_app(Hub()))) as client:
            r = await client.get("/static/drill.js")
            return r.status, r.headers.get("Cache-Control")
    assert asyncio.run(run()) == (200, "no-cache")
