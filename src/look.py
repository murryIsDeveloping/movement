"""Camera mode: a clap, or a pose of your choice, toggles it. While it's on a mouse button is held (right by default: WoW's
mouselook, which turns the character with the camera; left turns the camera alone) and the right hand steers like a
thumbstick. Backend injected for tests."""
import math
import sys
import traceback

DEFAULT = {
    "enabled": False,       # off: claps are only the clap pose
    "toggle": "clap",       # what toggles it: "clap", or the name of one of the active poses (its key is then never sent)
    "button": "right",      # held while it's on: "right" (mouselook, the character turns too), "left" (camera only)
                            # or "none" (moves the pointer, no button)
    "clap": 3.0,            # wrists closing speed (torso/s) that toggles, with them closer than clap_distance
    "clap_distance": 0.35,
    "lockout": 1.0,         # seconds after a toggle before the next one counts, and before keys come back
    "center": [0.05, -0.55],   # neutral right hand, as [right_wrist_out, right_wrist_up]: elbow bent, hand at your waist
    "deadzone": 0.12,       # torso; a hand this close to centre doesn't move the camera
    "reach": 0.5,           # torso from centre to full speed
    "speed": 900.0,         # pixels/s at full reach
    "invert_y": False,
}
NEAR_HANDS = 0.6   # torso; hands this close are clapping (or about to), so the stick freezes instead of swinging


def toggle_pose(poses, cfg: dict) -> int | None:
    """Position of the pose that toggles camera mode: the first enabled one named in cfg. None for the built-in clap,
    with camera mode off, or when no active pose has that name."""
    if not cfg["enabled"] or cfg["toggle"] == "clap":
        return None
    return next((i for i, p in enumerate(poses) if p.enabled and p.name == cfg["toggle"]), None)


class Look:
    """Camera mode's state: whether it's on and where the stick is. No output."""

    def __init__(self):
        self.on = False
        self.toggled_at = -math.inf
        self.triggered = False   # the toggle was on last frame: it toggles once per clap or pose, not every frame
        self.stick = (0.0, 0.0)   # hand from centre, torso; for the GUI
        self.velocity = (0.0, 0.0)   # pixels/s, screen axes (y down)

    def locked(self, t: float, cfg: dict) -> bool:
        """Just toggled: keys stay up, so the clap pose (and whatever else the clap set off) doesn't reach the game."""
        return t - self.toggled_at < cfg["lockout"]

    def update(self, f: dict, t: float, cfg: dict, pose_on: bool = False) -> None:
        """pose_on: the toggle pose (toggle_pose) is on this frame. Ignored when the toggle is the built-in clap."""
        clap = cfg["toggle"] == "clap"
        trigger = (f.get("clap", 0.0) > cfg["clap"] and f.get("wrists_distance", math.inf) < cfg["clap_distance"]
                   if clap else pose_on)
        if trigger and not self.triggered and not self.locked(t, cfg):
            self.on, self.toggled_at = not self.on, t
        self.triggered = trigger
        self.velocity = (0.0, 0.0)
        out, up = f.get("right_wrist_out"), f.get("right_wrist_up")
        if not self.on or out is None or up is None:
            self.stick = (0.0, 0.0)
            return
        x, y = out - cfg["center"][0], up - cfg["center"][1]
        self.stick = (x, y)
        if clap and f.get("wrists_distance", math.inf) < NEAR_HANDS:
            return
        m = math.hypot(x, y)
        if m <= cfg["deadzone"]:
            return
        s = min(1.0, (m - cfg["deadzone"]) / max(cfg["reach"] - cfg["deadzone"], 1e-6))
        v = cfg["speed"] * s * s / m   # squared: fine aim near the centre, fast swings at full reach
        self.velocity = (x * v, (y if cfg["invert_y"] else -y) * v)   # hand up = mouse up

    def stop(self) -> None:
        """Out of frame: off, so stepping back in never starts with the camera dragging."""
        self.on, self.triggered = False, False
        self.stick = self.velocity = (0.0, 0.0)


class LookOutput:
    """Holds the drag button and sends moves. Never raises: the mouse failing must not stop the camera loop."""

    def __init__(self, mouse):
        self.mouse = mouse
        self.down: str | None = None   # the button held
        self.rest = [0.0, 0.0]   # fractions of a pixel carried to the next frame, so slow turns still turn
        self.failed = False

    def _do(self, fn, *a) -> bool:
        try:
            fn(*a)
            return True
        except Exception:
            if not self.failed:
                self.failed = True
                print("mouse failed, camera mode can't move it:")
                traceback.print_exc()
            return False

    def apply(self, on: bool, button: str | None, velocity: tuple[float, float], dt: float) -> None:
        """on: moving. button: the one held while on ("left" or "right"), or None to move without one. A different
        one swaps them."""
        hold = button if on else None
        if self.down and self.down != hold:
            self._do(self.mouse.release, self.down)
            self.down = None
        if hold and not self.down:
            self.down = hold if self._do(self.mouse.press, hold) else None
        if not on or (hold and not self.down):   # a failed press: moving without it would sweep the pointer instead
            self.rest = [0.0, 0.0]
            return
        self.rest = [r + v * dt for r, v in zip(self.rest, velocity)]
        dx, dy = (int(r) for r in self.rest)
        if dx or dy:
            self.rest = [self.rest[0] - dx, self.rest[1] - dy]
            self._do(self.mouse.move, dx, dy)

    def release(self) -> None:
        self.apply(False, None, (0.0, 0.0), 0.0)


def system_mouse():
    """Left or right button plus relative moves. On Windows the moves go through SendInput: pynput's move jumps the cursor with
    SetCursorPos, which games reading raw mouse input (WoW's camera drag) don't see."""
    from pynput.mouse import Button, Controller

    ctl = Controller()
    move = _send_input_move() if sys.platform == "win32" else ctl.move

    class _Mouse:
        def press(self, b): ctl.press(Button[b])
        def release(self, b): ctl.release(Button[b])
        def move(self, dx, dy): move(dx, dy)

    return _Mouse()


def _send_input_move():
    import ctypes
    from ctypes import wintypes

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class INPUT(ctypes.Structure):   # the mouse member of the union only: it's the largest, so the size matches
        _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]

    send = ctypes.windll.user32.SendInput
    send.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    INPUT_MOUSE, MOUSEEVENTF_MOVE = 0, 0x0001

    def move(dx, dy):
        inp = INPUT(INPUT_MOUSE, MOUSEINPUT(int(dx), int(dy), 0, MOUSEEVENTF_MOVE, 0, 0))
        if send(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
            raise OSError("SendInput sent nothing (a game run as administrator blocks it)")

    return move
