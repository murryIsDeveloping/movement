# 06 · The per-frame logic lives inside the camera loop

**Severity:** medium (new outputs are wired in untested) · **Size:** small · **Related:** [03](03-recordings-lack-landmarks.md)

## Problem
What happens to each frame (pause, features, rules, camera mode, which keys and mouse moves go out) is written inline in `App.camera_loop`, between opening the webcam and encoding the preview JPEG. Nothing can run it without a camera and a pose model, so the tests check each part alone (`RuleEngine`, `Look`, `KeyState`, `LookOutput`) but not how they're joined.

Adding camera mode showed the cost: whether it pauses keys, holds them up through a toggle's lockout, stops on a pause and gates the drag on send keys is decided in that loop, and only a live session checks it. A wrong line there (keys sent during camera mode, a drag left held after a pause) would pass every test.

## Where
- `app.py`: `camera_loop`, from `self.frame_watch.update` to `self.mouse.apply`.

## Fix
1. Move the body of one frame into `App.step(p, t) -> dict`, which takes the landmarks (or `None`) and the time, updates rules and camera mode, applies keys and mouse, and returns the state to publish. `camera_loop` keeps the camera, the model, the fps count and the JPEG.
2. Test `step` with fixture bodies from `tests/fixtures.py`, a `FakeKB` and a `FakeMouse`: keys pause in camera mode and for the lockout, a pause releases the drag, keys off stops it.
3. With [03](03-recordings-lack-landmarks.md)'s joints in recordings, `step` is also what a replay would run.

## Acceptance
- `camera_loop` has no rule, key or mouse logic of its own.
- A test drives clap → steer → pause → back through `step` and checks every key and mouse event sent.
