"""Hold/release keys to mirror active poses. Backend injected for tests."""
import traceback

# pynput's Key names across platforms, listed so validation needs no keyboard backend.
# A name missing on this OS (insert on macOS, f21 off Windows) still fails at press time; KeyState rides that out.
KEY_NAMES = frozenset(
    "alt alt_l alt_r alt_gr backspace caps_lock cmd cmd_l cmd_r ctrl ctrl_l ctrl_r delete down end enter esc "
    "home insert left menu num_lock page_down page_up pause print_screen right scroll_lock shift shift_l shift_r "
    "space tab up media_next media_play_pause media_previous media_stop media_volume_down media_volume_mute "
    "media_volume_up".split()) | {f"f{i}" for i in range(1, 25)}


def valid_key(k) -> bool:
    """A single character or a pynput Key name: anything else makes pynput raise."""
    return isinstance(k, str) and (len(k) == 1 or k in KEY_NAMES)


class KeyState:
    def __init__(self, keyboard):
        self.kb = keyboard
        self.held: set[str] = set()
        self.failed: set[str] = set()   # keys already logged, so a bad one doesn't spam every frame

    def _do(self, fn, k) -> bool:
        """One key's press/release. Never raises: a bad key must not stop the camera loop."""
        try:
            fn(k)
            return True
        except Exception:
            if k not in self.failed:
                self.failed.add(k)
                print(f"key {k!r} failed, skipping it:")
                traceback.print_exc()
            return False

    def apply(self, wanted: set[str]) -> None:
        pressed = {k for k in wanted - self.held if self._do(self.kb.press, k)}
        for k in self.held - wanted:
            self._do(self.kb.release, k)
        self.held = (self.held & wanted) | pressed   # a failed press isn't held, so it's retried next frame

    def release_all(self) -> None:
        self.apply(set())


def pynput_keyboard():
    from pynput.keyboard import Controller, Key

    ctl = Controller()

    def resolve(k: str):
        return getattr(Key, k) if hasattr(Key, k) else k

    class _KB:
        def press(self, k): ctl.press(resolve(k))
        def release(self, k): ctl.release(resolve(k))

    return _KB()
