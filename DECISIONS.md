# Decisions

- **Pose held = key held, no tap mode.** WoW's GCD/cooldowns already rate-limit repeats. Only jump pulses (can't hold a jump).
- **Poses are feature rules, not recorded templates.** Each pose = conditions on named body features (arm raise angle, hip rise, step cadence…), tuned in the web GUI with live values. Template matching was tried first and dropped: user stands far from camera, so raw-landmark distance was too noisy and untunable.
- **Features in torso-length units or degrees, 13 body joints, xy only.** Invariant to camera distance and body size. Face/finger landmarks dropped as noise. z dropped: MediaPipe depth is unreliable from one camera.
- **Web GUI over native.** User is metres from the laptop; a browser tab with big text is readable, and the capture/trace tooling is cheap in HTML.
- **MediaPipe Tasks API, lite model.** mediapipe 1.x removed the legacy `solutions` API. Lite runs ~30fps on CPU; swap to `full`/`heavy` model file if accuracy is lacking.
- **pynput for keys.** OS-level events, same as a real keyboard. Needs Accessibility permission on macOS.
- **Camera backend forced to AVFoundation on macOS.** CAP_ANY picks FFmpeg first and fails to enumerate devices.
- **Packaged as its own app (PyInstaller) so Accessibility is granted to `Movement.app` alone**, not to Terminal or VS Code and everything they spawn. Per-OS build (`python build.py`); PyInstaller cannot cross-compile, so Windows builds on Windows.
- **Packaged config lives in the user data dir** (`~/Library/Application Support/Movement`, `%APPDATA%\Movement`), not inside the bundle. Bundles are read-only and replaced on rebuild. Dev runs keep `config.yaml` in the repo root.
- **App prompts for Accessibility on launch when packaged.** That is the only way macOS adds the app to the Accessibility list; otherwise the user has to find it by hand.
