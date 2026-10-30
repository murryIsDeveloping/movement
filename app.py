"""Pose → keyboard (and mouse, in camera mode) for WoW, with a browser GUI for defining poses.

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
from src.features import FEATURE_INFO, FeatureEngine
from src.keys import KEY_NAMES, MOUSE_BUTTONS, KeyState, pynput_keyboard
from src.landmarks import FrameWatch
from src.look import Look, LookOutput, system_mouse, toggle_pose
from src.overlay import draw_skeleton
from src.pose import PoseTracker
from src.rules import RuleEngine
from src.server import Hub, make_app
from src.trust import accessibility_trusted

KEY_LIST = sorted(KEY_NAMES)   # for the GUI's key check


class App:
    def __init__(self):
        self.cfg = cfgmod.load()
        self.lock = threading.Lock()
        self.rules = RuleEngine(cfgmod.poses_lenient(self.cfg))   # strict in set_config: a bad edit is refused
        self.features = FeatureEngine()
        self.frame_watch = FrameWatch(float(self.cfg.get("pause_after", 0.5)))
        self.keys = KeyState(pynput_keyboard())
        self.look = Look()
        self.mouse = LookOutput(system_mouse())
        self.hub = Hub()
        self.hub.on_config = self.set_config
        self.hub.on_reset = self.features.reset_baselines
        self.hub.get_config = lambda: dict(self.cfg)
        self.hub.on_quit = self.quit
        self.running = True
        self.send_keys = False   # session only: never saved, so a relaunch never sends keys into whatever has focus
        self.trusted = True   # macOS Accessibility: checked in run(), then rechecked by trust_loop

    def set_config(self, new: dict):
        new = dict(new)
        send = new.pop("send_keys", None)
        if "look" in new:   # the GUI sends only what it changes (enabled, toggle)
            new["look"] = {**self.cfg["look"], **new["look"]}
        if "clashes_ok" in new:
            new["clashes_ok"] = cfgmod.clean_clashes_ok(new["clashes_ok"])
        cfg = {**self.cfg, **new}
        rules = RuleEngine(cfgmod.poses_from(cfg))   # raises on a bad pose before anything changes
        with self.lock:
            self.cfg, self.rules = cfg, rules
            cfgmod.save(self.cfg)
            if send is not None:
                self.send_keys = bool(send)
            if not self.send_keys:
                self.keys.release_all()
                self.mouse.release()
            if not self.cfg["look"]["enabled"]:
                self.look.stop()
                self.mouse.release()

    def quit(self):
        self.running = False
        self.keys.release_all()
        self.mouse.release()
        threading.Timer(0.3, lambda: os._exit(0)).start()

    def trust_loop(self):
        """Rechecks Accessibility so granting it mid-session clears the GUI's warning. Its own thread, so the camera
        loop only reads the flag and never waits on the check."""
        while self.running:
            time.sleep(3)
            self.trusted = accessibility_trusted(prompt=False)

    def camera_loop(self):
        cam = self.cfg["camera"]
        camera = tracker = None
        try:
            camera = Camera(cam["index"], cam["width"], cam["height"])
            tracker = PoseTracker(cfgmod.ROOT / self.cfg["model"])
            t0 = time.monotonic()
            fps_t, fps_n, fps = 0.0, 0, 0.0   # fps_t in the same clock as t
            last_t = 0.0
            while self.running:
                frame = camera.read()
                if frame is None:
                    continue
                t = time.monotonic() - t0
                dt, last_t = min(t - last_t, 0.1), t   # a stalled frame doesn't fling the camera
                p = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), int(t * 1000))
                # Out of frame for a while (walked up to the camera): no features, so no baselines learnt from a
                # half-seen body, and every key up at once, holds included. A blip out of frame carries on as normal.
                paused, missing = self.frame_watch.update(p, t)
                if self.frame_watch.resumed:   # back in view, maybe at a new spot: re-learn standing height and knees
                    self.features.reset_baselines()
                feats = {} if paused or p is None else self.features.update(p, t)
                with self.lock:
                    if paused:
                        self.rules.release()
                        self.look.stop()
                    state = self.rules.update(feats, t)
                    look_cfg = self.cfg["look"]
                    toggle = toggle_pose(self.rules.poses, look_cfg)
                    held = self.rules.keys(skip=toggle)
                    poses = [pz.to_dict() for pz in self.rules.poses]
                    send = self.send_keys
                    if look_cfg["enabled"]:
                        self.look.update(feats, t, look_cfg, toggle in self.rules.active)
                    button = look_cfg["button"] if look_cfg["button"] in ("left", "right") else None
                    # camera mode pauses the game poses but not mouse clicks (bar the button the drag holds), and a
                    # toggle's clap must not reach the game as the clap pose
                    if self.look.locked(t, look_cfg):
                        out = set()
                    elif self.look.on:
                        out = {k for k in held if k in MOUSE_BUTTONS and k != f"mouse_{button}"}
                    else:
                        out = held
                    look = {"enabled": look_cfg["enabled"], "on": self.look.on, "stick": self.look.stick, "toggle": look_cfg["toggle"],
                            "button": look_cfg["button"], "deadzone": look_cfg["deadzone"], "reach": look_cfg["reach"]}
                    moving, velocity = send and self.look.on, self.look.velocity
                self.keys.apply(out if send else set())
                self.mouse.apply(moving, button, velocity, dt)

                fps_n += 1
                if t - fps_t > 1.0:
                    fps, fps_n, fps_t = fps_n / (t - fps_t), 0, t
                draw_skeleton(frame, p)
                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                self.hub.publish(jpeg.tobytes(), {
                    "t": t, "features": feats, "poses": poses, "state": state, "body": p is not None, "paused": paused, "missing": missing,
                    "held": sorted(held), "blocked": sorted(held - out), "look": look, "send_keys": send, "fps": round(fps, 1), "feature_info": FEATURE_INFO, "key_names": KEY_LIST,
                    "trusted": self.trusted, "clashes_ok": self.cfg["clashes_ok"],
                })
        except Exception:
            traceback.print_exc()
            self.hub.publish(None, {"error": traceback.format_exc().strip().splitlines()[-1]})
        finally:
            self.keys.release_all()
            self.mouse.release()
            if camera:
                camera.release()
            if tracker:
                tracker.close()

    def run(self):
        threading.Thread(target=self.camera_loop, daemon=True).start()
        port = int(self.cfg["port"])
        url = f"http://localhost:{port}"
        print(f"GUI at {url}")
        self.trusted = accessibility_trusted(prompt=paths.frozen())
        if not self.trusted:
            print("Accessibility not granted: keys will not reach other apps")
        threading.Thread(target=self.trust_loop, daemon=True).start()
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        try:
            web.run_app(make_app(self.hub), host="127.0.0.1", port=port, print=None)
        finally:
            self.running = False
            self.keys.release_all()
            self.mouse.release()


if __name__ == "__main__":
    App().run()
