# movement

Webcam pose → keyboard, so WoW grinding becomes a workout.
Pose held = key held. WoW's own cooldowns handle repeat.

Poses are rules on body features (arm raise angle, hip rise, step cadence…), tuned in a browser GUI with live values. No code to add a pose.

## Packaged app (recommended)

Build on the OS you will run it on. PyInstaller does not cross-compile.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
.venv/bin/python build.py                      # Windows: .venv\Scripts\python build.py
```

Output: `dist/Movement.app` (macOS) or `dist/Movement/Movement.exe` (Windows). Move it wherever you like; drag to Applications on mac.

Config lives in `~/Library/Application Support/Movement/config.yaml` (mac) or `%APPDATA%\Movement\config.yaml` (Windows). Survives rebuilds.

### macOS permissions (one-off)

First launch prompts for **Camera** and **Accessibility**. Both go to `Movement` only, nothing else inherits them. Accessibility is what lets the app press keys in WoW. Revoke any time in System Settings > Privacy & Security.

The app is ad-hoc signed, not notarised. If Gatekeeper blocks it: right-click > Open, once.

### Windows

No special permissions. Run as a normal user, not admin: WoW must run at the same privilege level or keys are blocked. Windows Defender may flag an unsigned PyInstaller exe; allow it.

## Dev run

```sh
.venv/bin/python app.py
```

Opens `http://localhost:8765`. Config is `config.yaml` in the repo root. Camera and Accessibility permission then go to whatever runs Python (Terminal, VS Code…), which is broad; prefer the packaged app for real use.

Model `models/pose_landmarker_lite.task` is included. If missing:

```sh
curl -L -o models/pose_landmarker_lite.task https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
```

## GUI

- **send keys to game**: off by default. Tick when WoW is focused and you want keys delivered.
- **+ new pose**: name, key, conditions (`feature > value`). All conditions true → key held. Dot goes green per condition live.
- **hold**: seconds the key stays down after the pose ends. Turns a one-frame punch into a proper press and rides out brief tracking dropouts; costs that much delay on release. 0 = release immediately.
- **↑ / ↓**: reorder poses.
- **stick figure** on each pose: a body position that fires it, mirrored like the camera preview. Jump and jog animate.
- **clashes (N)**: opens a side panel (Esc closes) listing pairs of poses on the same body part (same feature, or same arm) that can fire together, with the overlapping range and a figure of it. Poses on separate body parts (jog + arm raise) are combos and are not listed.
- **capture**: 3s countdown, records 4s of movement, ranks which features moved most, suggests thresholds. Scrub frames, tick features, apply. Set **start** to another pose (e.g. jump) to arm it hands-free: walk back into position, do that pose, and the countdown begins. Beeps mark each step.
- **reset baselines**: hip/knee rest heights re-learn. Use after moving camera or stepping back.
- **export / import**: config.yaml download and upload.

Stand 2–3 m back, full body in frame, plain background, even light.

## Tests

```sh
.venv/bin/pytest
```
