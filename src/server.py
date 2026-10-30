"""aiohttp server: static UI, MJPEG preview, websocket for live state + config edits."""
import asyncio
import json
import threading
import time
from collections import deque

import yaml
from aiohttp import web

from src import library, paths
from src.rules import Pose

STATIC = paths.resource_root() / "static"
RECORDINGS = paths.config_path().parent / "recordings"
DEV = not paths.frozen()   # drill recordings are for debugging with Claude: running from source only, never the packaged app


class Hub:
    """Shared between camera thread and web loop."""

    def __init__(self):
        self.lock = threading.Lock()
        self.jpeg: bytes | None = None
        self.state: dict = {}
        self.sockets: set[web.WebSocketResponse] = set()
        self.frames: deque[dict] = deque(maxlen=120)
        self.on_config = None  # callback(dict) from UI
        self.on_reset = None
        self.on_quit = None
        self.get_config = lambda: {}

    def publish(self, jpeg: bytes | None, state: dict):
        with self.lock:
            if jpeg is not None:
                self.jpeg = jpeg
            self.state = state
            if DEV and "t" in state:   # every camera frame, not just the broadcast ones, so drill recordings miss no spikes
                self.frames.append({"t": round(state["t"], 3), "body": state["body"], "paused": state["paused"], "missing": state["missing"], "f": state["features"],
                                    "on": [i for i, s in enumerate(state["state"]) if s["active"]]})

    def take(self) -> str:
        """The broadcast: latest state plus the frames since the last one."""
        with self.lock:
            payload = json.dumps({**self.state, "frames": list(self.frames)})
            self.frames.clear()
        return payload


async def index(_):
    return web.FileResponse(STATIC / "index.html")


async def stream(request):
    hub: Hub = request.app["hub"]
    resp = web.StreamResponse(headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"})
    await resp.prepare(request)
    try:
        while True:
            with hub.lock:
                jpeg = hub.jpeg
            if jpeg:
                await resp.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                 + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n")
            await asyncio.sleep(1 / 20)
    except (ConnectionResetError, asyncio.CancelledError):
        pass
    return resp


async def config_get(request):
    hub: Hub = request.app["hub"]
    body = yaml.safe_dump(hub.get_config(), sort_keys=False, allow_unicode=True)
    return web.Response(text=body, content_type="text/yaml",
                        headers={"Content-Disposition": 'attachment; filename="movement-config.yaml"'})


async def config_put(request):
    hub: Hub = request.app["hub"]
    try:
        data = yaml.safe_load(await request.text()) or {}
        if "poses" not in data or not isinstance(data["poses"], list):
            raise ValueError("no 'poses' list in file")
        for p in data["poses"]:
            Pose.from_dict(p)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    hub.on_config(data)
    return web.json_response({"ok": True, "poses": len(data["poses"])})


async def library_get(_):
    return web.json_response({**library.load(), "edit_builtins": DEV})


async def library_put(request):
    """The GUI edits the library locally and sends the whole thing back. Built-ins only change running from source."""
    try:
        library.save(await request.json(), edit_builtins=DEV)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    return web.json_response({"ok": True})


async def recording_post(request):
    """Saves a drill run (prompts, hits, every frame's features) for looking at later."""
    data = await request.json()
    RECORDINGS.mkdir(exist_ok=True)
    path = RECORDINGS / f"drill-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    print(f"recording saved: {path}")
    return web.json_response({"ok": True, "path": str(path)})


async def ws_handler(request):
    hub: Hub = request.app["hub"]
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    hub.sockets.add(ws)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get("type") == "config" and hub.on_config:
                    try:
                        hub.on_config(data["config"])
                    except ValueError as e:   # bad pose: keep the old config and the socket, and tell the page why
                        print(f"config rejected: {e}")
                        await ws.send_str(json.dumps({"type": "error", "error": str(e)}))
                elif data.get("type") == "reset_baselines" and hub.on_reset:
                    hub.on_reset()
                elif data.get("type") == "quit" and hub.on_quit:
                    hub.on_quit()
    finally:
        hub.sockets.discard(ws)
    return ws


async def broadcaster(app):
    hub: Hub = app["hub"]
    while True:
        payload = hub.take()
        dead = []
        for ws in list(hub.sockets):
            try:
                await ws.send_str(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            hub.sockets.discard(ws)
        await asyncio.sleep(1 / 15)


async def _start_bg(app):
    app["bg"] = asyncio.create_task(broadcaster(app))


def make_app(hub: Hub) -> web.Application:
    app = web.Application(client_max_size=64 * 1024 ** 2)   # a minute of drill frames is over the default 1 MB
    app["hub"] = hub
    app.router.add_get("/", index)
    app.router.add_get("/stream", stream)
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/config", config_get)
    app.router.add_put("/config", config_put)
    app.router.add_get("/library", library_get)
    app.router.add_put("/library", library_put)
    if DEV:
        app.router.add_post("/recording", recording_post)
    app.router.add_static("/static", STATIC)
    app.on_startup.append(_start_bg)
    return app
