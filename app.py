"""Pose → keyboard for WoW, with a browser GUI for defining poses.

  python app.py          start camera + GUI at http://localhost:8765
"""
import os
import threading
import time
import traceback
import webbrowser

import cv2
from aiohttp import web

from src import config as cfgmod
from src import paths

paths.setup_frozen_env()
from src.camera import Camera
from src.features import FEATURES, FeatureEngine
from src.keys import KeyState, pynput_keyboard
from src.overlay import draw_skeleton
from src.pose import PoseTracker
from src.rules import RuleEngine
from src.server import Hub, make_app
from src.trust import accessibility_trusted


class App:
    def __init__(self):
        self.cfg = cfgmod.load()
        self.lock = threading.Lock()
        self.rules = RuleEngine(cfgmod.poses_from(self.cfg))
        self.features = FeatureEngine()
        self.keys = KeyState(pynput_keyboard())
        self.hub = Hub()
        self.hub.on_config = self.set_config
        self.hub.on_reset = self.features.reset_baselines
        self.hub.get_config = lambda: dict(self.cfg)
        self.hub.on_quit = self.quit
        self.running = True

    def set_config(self, new: dict):
        with self.lock:
            self.cfg = {**self.cfg, **new}
            self.rules = RuleEngine(cfgmod.poses_from(self.cfg))
            cfgmod.save(self.cfg)
            if not self.cfg.get("send_keys"):
                self.keys.release_all()

    def quit(self):
        self.running = False
        self.keys.release_all()
        threading.Timer(0.3, lambda: os._exit(0)).start()

    def camera_loop(self):
        cam = self.cfg["camera"]
        camera = tracker = None
        try:
            camera = Camera(cam.get("index", 0), cam.get("width", 640), cam.get("height", 480))
            tracker = PoseTracker(cfgmod.ROOT / self.cfg["model"])
            t0 = time.monotonic()
            fps_t, fps_n, fps = t0, 0, 0.0
            while self.running:
                frame = camera.read()
                if frame is None:
                    continue
                t = time.monotonic() - t0
                p = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), int(t * 1000))
                feats = self.features.update(p, t) if p is not None else {}
                with self.lock:
                    state = self.rules.update(feats)
                    wanted = self.rules.keys() if self.cfg.get("send_keys") else set()
                    poses = [pz.to_dict() for pz in self.rules.poses]
                    send = bool(self.cfg.get("send_keys"))
                self.keys.apply(wanted)

                fps_n += 1
                if t - (fps_t - t0) > 1.0:
                    fps, fps_n, fps_t = fps_n / (t - (fps_t - t0)), 0, time.monotonic()
                draw_skeleton(frame, p)
                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                self.hub.publish(jpeg.tobytes(), {
                    "features": feats, "poses": poses, "state": state, "body": p is not None,
                    "held": sorted(self.rules.keys()), "send_keys": send, "fps": round(fps, 1),
                    "feature_info": {k: {"desc": d, "unit": u} for k, (d, u) in FEATURES.items()},
                })
        except Exception:
            traceback.print_exc()
            self.hub.publish(None, {"error": traceback.format_exc().strip().splitlines()[-1]})
        finally:
            self.keys.release_all()
            if camera:
                camera.release()
            if tracker:
                tracker.close()

    def run(self):
        threading.Thread(target=self.camera_loop, daemon=True).start()
        port = int(self.cfg.get("port", 8765))
        url = f"http://localhost:{port}"
        print(f"GUI at {url}")
        if not accessibility_trusted(prompt=paths.frozen()):
            print("Accessibility not granted: keys will not reach other apps")
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        try:
            web.run_app(make_app(self.hub), host="127.0.0.1", port=port, print=None)
        finally:
            self.running = False
            self.keys.release_all()


if __name__ == "__main__":
    App().run()
