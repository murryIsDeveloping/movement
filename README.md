# movement

Webcam pose → keyboard (and mouse, for an MMO's camera), so MMO grinding becomes a workout.
Pose held = key held. The game's own cooldowns handle repeat.

Poses are rules on body features (arm raise angle, hip rise, step cadence…), tuned in a browser GUI with live values. No code to add a pose.

## Packaged app (recommended)

Build on the OS you will run it on. PyInstaller does not cross-compile.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt      # Windows: .venv\Scripts\pip
.venv/bin/python build.py                      # Windows: .venv\Scripts\python build.py
```

Output: `dist/Movement.app` (macOS) or `dist/Movement/Movement.exe` (Windows). Move it wherever you like; drag to Applications on mac.

Config lives in `~/Library/Application Support/Movement/config.yaml` (mac) or `%APPDATA%\Movement\config.yaml` (Windows). Survives rebuilds. A new install starts with the poses of the built-in *mmo hunter* group, linked to the library.

### macOS permissions (one-off)

First launch prompts for **Camera** and **Accessibility**. Both go to `Movement` only, nothing else inherits them. Accessibility is what lets the app press keys in your game. Revoke any time in System Settings > Privacy & Security.

The app is ad-hoc signed, not notarised. If Gatekeeper blocks it: right-click > Open, once.

### Windows

No special permissions. Run as a normal user, not admin: the game must run at the same privilege level or keys are blocked. Windows Defender may flag an unsigned PyInstaller exe; allow it.

## Dev run

```sh
.venv/bin/python app.py      # Windows: .venv\Scripts\python app.py
```

Opens `http://localhost:8765`. Config is `config.yaml` in the repo root. Camera and Accessibility permission then go to whatever runs Python (Terminal, VS Code…), which is broad; prefer the packaged app for real use.

Model `models/pose_landmarker_lite.task` is included. If missing:

```sh
curl -L -o models/pose_landmarker_lite.task https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
```

## GUI

- **keys off / KEYS ON**: the big button next to the status pills. Off at every launch, since it is never saved to `config.yaml` or an export; click it when the game is focused and you want keys delivered. While on, the button is solid green and the camera preview has a green border. While off, the held-key chips under the preview are grey, struck through and labelled *not sent*.
- **sound**: ticked by default (remembered per browser). While keys are on, a low double beep means tracking paused (out of frame or no body) and every key was released; one high beep means it resumed. Lets you hear why your character stopped with the game focused. Sound starts after your first click on the keys button in this tab.
- **camera mode**: off by default (saved in `config.yaml`). Tick it, then clap to switch camera mode on and clap again to switch it off. To use another position, pick one of your poses in the dropdown next to it instead of **clap**: that pose toggles camera mode and never sends its key (its card is tagged **camera toggle** and its key struck through). Make and tune it like any other pose; a delay of half a second or so stops it toggling by accident. The second dropdown sets what your right hand does while it's on: **right click drag** (the default: MMO mouselook, the camera turns and your character turns to face where it looks), **left click drag** (the camera turns alone) or **mouse move** (moves the pointer with no button held, to click things with a mouse-button pose). Your right hand steers like a thumbstick: neutral is at your waist with the elbow bent, and the further you move it, the faster the camera turns (hand up looks up). A **CAMERA** badge over the preview shows the stick, and a rising beep marks on, a falling one off. Game poses pause until you toggle it off, except poses bound to a mouse button (other than the one the drag holds), so you can still click; and keys stay up for 1s after each toggle so a clap doesn't also fire the clap pose. The drag is only sent while keys are on; stepping out of frame turns camera mode off. The button, neutral spot, dead zone, reach, speed, clap strength and `invert_y` are under `look:` in `config.yaml`.
- **+ add pose**: a searchable list of the library's poses, with their stick figures. Click one (or Enter for the first match) and a copy is added to your poses, ready to tune; ones you already have are tagged *in your poses*, and clicking one adds a second copy. New poses are made in the library.
- **pose card**: name, key, conditions (`feature > value`). All conditions true → key held. Dot goes green per condition live. Under each condition is what its feature measures; values carry units: ° degrees, t torso lengths (shoulders to hips), /s per second. The card's second row holds hold, delay, reorder, + condition, capture, → library and delete.
- **key** (on poses, presets and group chips): click it and press the key you want bound, or click it again with the mouse button you want (`mouse_left`, `mouse_right`, `mouse_middle`; e.g. lift your left leg to left-click): space, f1, an arrow, left or right shift/ctrl/alt (bound when released alone; a pose holds one key, so Shift+A binds `a`). On a pose card a letter or digit saves at once too; in the library, letters and digits are typed and saved with Enter or by clicking away. Names the browser can't capture (`num_lock`, `print_screen`, `tab`, since Tab moves on to the next field) are typed the same way; Esc while typing a name cancels it, otherwise Esc binds `esc`. Numpad digits bind the main-row digit. In a group chip, Backspace clears it back to the preset's key. A key pynput can't press is outlined red and not saved.
- **hold**: seconds the key stays down after the pose ends. Turns a one-frame punch into a proper press and rides out brief tracking dropouts; costs that much delay on release. 0 = release immediately.
- **delay**: seconds the pose must be held before its key goes down. Stops a pose firing while an arm passes through it on the way somewhere else (raising a hand overhead, a sideways punch ending arm-out); costs that much delay on press. 0 = press immediately.
- **↑ / ↓**: reorder poses.
- **delete**: removes a pose at once; **undo** on the bar above the poses puts it back, for 6s after (latest delete only).
- **drill**: full-screen test. First set its **length** (minutes), **rest** (seconds of neutral before the next pose), **time to hit** (seconds to get into a pose, or between reps, before it counts as a miss), **positions** (hold or reps), **hold** (seconds) and **reps**; they're remembered, and **again** reuses them. Defaults are 1 min, 3s, 10s, hold, 10s and 5; a long drill with a short rest makes it a workout. It shows a random enabled pose in large text with its stick figure, and what to do with it:
  - **Positions** (chair, arm out, a squat) are held: the name turns green and counts down while you're in it. Dropping out for up to 1s (a wobble) pauses the countdown; longer starts it over. Set **positions** to **reps** to do them as reps instead: a squat each time you sink into it, a lateral raise each time the arm comes out.
  - **Movements**, poses that need motion (jump, jog, punch, swipe), are always reps: each time the pose turns on is one, counted aloud with voice on. Movements you keep going (jog, stride) are kept up for the hold time instead, since a rep would mean stopping each time.

  When it's done a tick appears, then it says **neutral**: go back to standing with arms down. The next prompt comes once the rest has passed and nothing is firing. When the time's up it lists hits, average time, any other poses that fired while you were prompted, and any that fired on the way back to neutral. Esc stops it. The drill turns send keys off while it runs, since its own page has the focus and a pose's key would land there (space scrolls it), and turns it back on when the drill ends; a tag in its corner shows **keys on** or **keys off**. Reloading the page mid-drill leaves keys off. When running from source (not the packaged app), each run (even one stopped early) is saved to `recordings/drill-<date>-<time>.json` next to `config.yaml` for debugging with Claude: the poses, every prompt/hit/miss/wrong fire, and every frame's features and active poses.
- **learn**: the drill's screen without the clock, for learning poses. Goes through each active pose in order (or a group's, with that group's **learn** button in the groups panel, which loads the group first if it isn't active), showing its stick figure, its preset's notes and a live tick-list of its conditions. Hold a position for 5s, or do a movement 3 times, and it moves on; **skip** gives up on one. Ends with the drill's results table, and is recorded as `recordings/learn-<date>-<time>.json` when running from source.
- **coaching** (drill and learn): while a pose isn't hit, a yellow line under the prompt says what to fix, for the unmet condition you're furthest from ("raise your left arm higher", "squat lower"). Positions come before movements, so a punch pose asks for the arm out before asking for the punch. It appears after 1s, so moving into the pose doesn't flicker it. With **voice** ticked (top bar; remembered per browser) the browser reads out each pose's name as it's prompted, and the cue from 2s in: a new cue at most every 2.5s, the same one again every 5s. Each spoken cue is a `coach` event in the recording.
- **stick figure** on each pose: a body position that fires it, mirrored like the camera preview. Jump and jog animate.
- **clashes (N)**: opens a side panel (Esc closes) listing pairs of poses on the same body part (same feature, or same arm) that can fire together, with the overlapping range and a figure of it. Poses on separate body parts (jog + arm raise) are combos and are not listed. The count is worked out in the background after each change and shows **clashes (…)** until it's ready; a big group takes a while the first time.
- **Loading poses…**: loading a group (or importing) redraws every pose's stick figure, a second or two for a big group the first time. A loading screen covers it, with the camera preview and live updates paused meanwhile. Figures are remembered, so going back to a group is quick.
- **group picker** (next to *Poses*): shows which group the active poses are, or *custom* once you've added, removed, rebound or tuned any. Pick another group to switch to it, the same as its **load**. It only asks before replacing when your poses are custom, since switching away from an untouched group loses nothing.
- **library**: side panel of every pose you can add (presets), each marked **built-in** or **custom** (yours), with notes on how to do it. **+ new pose** at the top makes a blank custom one and adds it to your poses to tune live.
  - **Built-ins** ship with the app (`presets.yaml`) and are locked so they can't be broken: add one, **clone** it into your own preset to rework, or put it in your own groups. Your presets and groups are saved in `my_presets.yaml` next to `config.yaml`. Built-ins are locked even running from source; they are tuned by editing `presets.yaml` directly (by hand or with Claude), so nothing clicked in the app can change them.
  - Your custom presets' name, default key and notes edit in place. **show** on one you have in your poses scrolls to its card.
- **groups**: side panel (the button next to the group picker). A **group** is a setup for one game or class (built-in: *mmo hunter*, *mmo mage*, *platformer*, *light movements*, *workout*, *yoga*): its presets plus the key each presses in that game, overriding the preset's default key (blank = default). **load** replaces the active poses with a group, **add** appends it, **learn** goes through it. Make one empty, with **+ group from your poses** (which keeps the keys they're bound to now), by **clone**-ing a built-in group, or from the library: tick presets with **select to group** and **+ group from ticked**, or use a preset's **+ group…** menu.
- **badge** on each pose: **built-in** or **custom** for the library pose it came from, **changed** when it's been tuned since it was last saved to the preset, or **not in library**. **→ library** saves the pose's conditions and timings into its preset; for a built-in (locked) it saves a new custom one, "<name> tuned", instead. Keys are bindings, not tuning: they belong to groups and aren't saved back.
- **capture**: 3s countdown, records 4s of movement, ranks which features moved most, suggests thresholds. Scrub frames, tick features, apply. Set **start** to another pose (e.g. jump) to arm it hands-free: walk back into position, do that pose, and the countdown begins. Beeps mark each step.
- **reset baselines**: hip/knee rest heights re-learn. Use after moving camera or stepping back.
- **export / import**: config.yaml download and upload.

Stand 2–3 m back, full body in frame, plain background, even light.

**Paused: not fully in frame**: if any joint the poses read (nose, shoulders, elbows, wrists, hips, knees) is off the edge of the picture or hidden for half a second straight (`pause_after` in `config.yaml`), every key is released and nothing fires until you're back in full view. The banner names the joints that are out. Shorter blips, like your head leaving the top of the picture mid-jump, don't pause. Feet may be cut off, except for poses using **knee angle** (hip-knee-ankle): it reads blank, so its condition fails, while that ankle is out of frame, and the coach says to step back. Seen from the front, knee angle and **knee out** catch a knee bending or opening out to the side (warrior, goddess, tree); a knee bending towards the camera (a squat, chair) barely shows, so those still use hip drop. Arms raised overhead count too: if hands-up poses pause, step back. The drill's clock stops while paused.

## Tests

```sh
.venv/bin/pytest             # Windows: .venv\Scripts\python -m pytest
```
