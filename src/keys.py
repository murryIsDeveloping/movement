"""Hold/release keys to mirror active poses. Backend injected for tests."""


class KeyState:
    def __init__(self, keyboard):
        self.kb = keyboard
        self.held: set[str] = set()

    def apply(self, wanted: set[str]) -> None:
        for k in wanted - self.held:
            self.kb.press(k)
        for k in self.held - wanted:
            self.kb.release(k)
        self.held = set(wanted)

    def pulse(self, key: str) -> None:
        if key in self.held:
            return
        self.kb.press(key)
        self.kb.release(key)

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
