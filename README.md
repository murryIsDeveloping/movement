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

- **keys off / KEYS ON**: the big button next to the status pills. Off by default; click it when WoW is focused and you want keys delivered. While on, the button is solid green and the camera preview has a green border. While off, the held-key chips under the preview are grey, struck through and labelled *not sent*.
- **sound**: ticked by default (remembered per browser). While keys are on, a low double beep means tracking paused (out of frame or no body) and every key was released; one high beep means it resumed. Lets you hear why your character stopped with WoW focused. Sound starts after your first click on the keys button in this tab.
- **+ new pose**: name, key, conditions (`feature > value`). All conditions true → key held. Dot goes green per condition live.
- **key** (on poses, presets and group chips): click it and press the key you want bound: space, f1, an arrow, left or right shift/ctrl/alt (bound when released alone; a pose holds one key, so Shift+A binds `a`). On a pose card a letter or digit saves at once too; in the library, letters and digits are typed and saved with Enter or by clicking away. Names the browser can't capture (`num_lock`, `print_screen`, `tab`, since Tab moves on to the next field) are typed the same way; Esc while typing a name cancels it, otherwise Esc binds `esc`. Numpad digits bind the main-row digit. In a group chip, Backspace clears it back to the preset's key. A key pynput can't press is outlined red and not saved.
- **hold**: seconds the key stays down after the pose ends. Turns a one-frame punch into a proper press and rides out brief tracking dropouts; costs that much delay on release. 0 = release immediately.
- **delay**: seconds the pose must be held before its key goes down. Stops a pose firing while an arm passes through it on the way somewhere else (raising a hand overhead, a sideways punch ending arm-out); costs that much delay on press. 0 = press immediately.
- **↑ / ↓**: reorder poses.
- **drill**: full-screen test. Shows a random enabled pose in large text; strike it and a tick appears, then it says **neutral**: go back to standing with arms down. The next prompt comes once 3s have passed and nothing is firing (10s with no hit counts as a miss). Runs for a minute, then lists hits, average time, any other poses that fired while you were prompted, and any that fired on the way back to neutral. Esc stops it. When running from source (not the packaged app), each run (even one stopped early) is saved to `recordings/drill-<date>-<time>.json` next to `config.yaml` for debugging with Claude: the poses, every prompt/hit/miss/wrong fire, and every frame's features and active poses.
- **stick figure** on each pose: a body position that fires it, mirrored like the camera preview. Jump and jog animate.
- **clashes (N)**: opens a side panel (Esc closes) listing pairs of poses on the same body part (same feature, or same arm) that can fire together, with the overlapping range and a figure of it. Poses on separate body parts (jog + arm raise) are combos and are not listed.
- **library**: side panel of preset poses, each marked **tested** or **untested**, with notes on how to do it, and **groups** of them.
  - **Built-ins** ship with the app (`presets.yaml`) and are locked so they can't be broken: **use** one, **clone** it into your own preset to rework, or put it in your own groups. Your presets and groups are saved in `my_presets.yaml` next to `config.yaml`. Running from source, built-ins are editable too, which is how they get tuned before shipping.
  - **use** adds a preset to the active poses; **+ new preset** starts a blank one there. Your own presets' name, default key, notes and status edit in place.
  - A **group** is a setup for one game or class (built-in examples: *wow hunter*, *wow mage*, *mario*): its presets plus the key each presses in that game, overriding the preset's default key (blank = default). **load** replaces the active poses with a group, **add** appends it. Make one empty, by ticking presets and **+ group from ticked**, with a preset's **+ group…** menu, by **clone**-ing a built-in group, or with **+ group from active poses**, which keeps the keys the active poses are bound to now.
- **badge** on each pose: its preset's status (click to flip tested/untested), **changed** when it's been tuned since it was last saved to the preset, or **not in library**. **→ library** saves the pose's conditions and timings into its preset; for a built-in (locked) it saves a new preset of yours, "<name> tuned", instead. Keys are bindings, not tuning: they belong to groups and aren't saved back.
- **capture**: 3s countdown, records 4s of movement, ranks which features moved most, suggests thresholds. Scrub frames, tick features, apply. Set **start** to another pose (e.g. jump) to arm it hands-free: walk back into position, do that pose, and the countdown begins. Beeps mark each step.
- **reset baselines**: hip/knee rest heights re-learn. Use after moving camera or stepping back.
- **export / import**: config.yaml download and upload.

Stand 2–3 m back, full body in frame, plain background, even light.

**Paused: not fully in frame**: if any joint the poses read (nose, shoulders, elbows, wrists, hips, knees) is off the edge of the picture or hidden for half a second straight (`pause_after` in `config.yaml`), every key is released and nothing fires until you're back in full view. The banner names the joints that are out. Shorter blips, like your head leaving the top of the picture mid-jump, don't pause. Feet may be cut off. Arms raised overhead count too: if hands-up poses pause, step back. The drill's clock stops while paused.

## Tests

```sh
.venv/bin/pytest
```
