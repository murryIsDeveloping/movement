# movement

Webcam pose → keyboard (WoW, Mario), plus drills, learn mode and coaching for workouts and yoga. Python backend (MediaPipe, aiohttp, pynput), plain-JS browser GUI. See `README.md` for features and `DECISIONS.md` for why things are the way they are.

- `app.py`: camera loop. `src/features.py`: body features (the stick figure in `static/figure.js` re-implements the static ones: change both). `src/rules.py`: poses as feature conditions. `presets.yaml`: built-in presets and groups.
- `static/drill.js`: drill, learn, coaching, holds and reps. `static/figure.js`: stick figure solver and clashes.
- Run: `.venv\Scripts\python app.py` (opens http://localhost:8765). Test: `.venv\Scripts\python -m pytest`. No JS tests or runtime yet.
- Drill recordings (`recordings/`) are dev-only, for debugging poses with Claude; never in the packaged build.

## Issues

`issues/` holds one file per issue, by kind (`architecture/`, `ui/`), indexed in `issues/README.md`. When you hit an architectural problem while working (something structural that made a change harder, riskier or impossible to check), add an issue to `issues/architecture/` or update the existing one, and its row in the index, so it's on record for a future fix. Follow the existing files' format.
