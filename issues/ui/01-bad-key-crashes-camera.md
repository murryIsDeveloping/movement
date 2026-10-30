# 01 · A bad key name crashes the camera loop

**Severity:** high (ends the session) · **Size:** small · **Related:** [05](05-key-capture-field.md)

## Problem
The pose key field saves on every keystroke. Typing `space` saves `s`, `sp`, `spa`, `spac` and `space` in turn, and clearing the field saves `""`. Nothing validates the key.

pynput only accepts a single character or a `Key` member name. If **send keys** is on and the pose fires while the key is half-typed or empty, pynput raises. The exception escapes the camera loop and the camera thread exits. The GUI shows `camera error: ValueError…`, and nothing works again until the app is restarted.

## Where
- `static/index.html:286`: the `.key` input's `oninput` calls `scheduleSave()` on every keystroke.
- `src/keys.py:25-30`: `resolve()` passes unknown strings straight to `ctl.press`.
- `src/rules.py:37-49`: `Pose.from_dict` validates features and ops, but not `key`.
- `app.py:85`: `self.keys.apply(...)` runs inside the single `try` that wraps the whole camera loop (`app.py:61-98`).

## Repro
1. Tick **send keys to game**.
2. In a pose whose condition you can trigger, change the key to `spac`.
3. Do the pose. The camera pill changes to `camera error` and the preview freezes.

## Fix
1. Add a `valid_key(k)` helper next to `resolve` in `src/keys.py`. It returns true for a single character or a `pynput.keyboard.Key` attribute name. Either import pynput lazily or list the names, so `rules.py` stays testable without a keyboard backend.
2. In `Pose.from_dict`, raise `ValueError(f"pose {name!r}: unknown key {key!r}")` when the key is invalid, the same way unknown features are handled. `set_config` then rejects the change and keeps the old config, and **import** fails with a clear message.
3. In the GUI, save the key on `change` (blur or Enter) instead of on `input`. If the value isn't a known key, mark the field invalid (red border, with the reason as its title) and don't save it.
4. As a safety net, make `KeyState.apply` catch an error on a single key, log it once and carry on, so a bad key can never stop tracking.

## Acceptance
- With send keys on, typing a partial or empty key never stops the camera.
- Importing a config containing `key: spac` fails with `unknown key 'spac'`.
- Tests in `tests/` cover `Pose.from_dict` rejecting a bad key, and `KeyState.apply` surviving a backend that raises.
