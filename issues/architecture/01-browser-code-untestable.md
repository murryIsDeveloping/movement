# 01 · The browser code can't be tested

**Severity:** high (slows every GUI change) · **Size:** medium · **Related:** [02](02-feature-metadata-scattered.md)

## Problem
Drill, learn, coaching, the stick-figure solver and clash detection are all JavaScript, and none of it has tests. There is no JS runtime in the dev setup, so even a syntax error only shows up in the running app. Building holds and reps meant writing throwaway harness pages and running them in Chrome to check the logic.

Fixing stick figures from a learn run (2026-10-30) hit it again. Each solver change (a forward fold, a wide-stance start, a cost on folding) had to be checked by solving every preset in Chrome. A first try at the fold quietly bent eight unrelated figures forward to reach their arm heights, and was only caught by that sweep. Solving all 51 presets in one call outran the browser tool's 45s limit, so it had to be split into batches.

The drill logic is also hard to test in isolation. `drillTick` reads the page's globals (`poses`, `state`, `live`, `paused`), the clock (`performance.now`) and the DOM, decides what happens and renders, all in one function. Scripts share state through globals and depend on load order (`drill.js` is loaded before the main script and uses its variables at call time).

## Where
- `static/drill.js:278`: `drillTick` mixes state changes, events and rendering. `drillProgress` (`static/drill.js:253`) is the closest thing to a pure step, but it still reads `state` and calls `beep`/`say`.
- `static/figure.js`: `solveFigure`, `figFeatures`, `findClashes` are pure in practice but read the globals `info` and `poses`.
- `static/drill.js:1-2`, `static/figure.js:1`: the comments listing which globals each file borrows.

## Fix
1. Add Node as a dev dependency (no build step for the app itself) and a `node --test` suite under `tests/js/`, run alongside `pytest`.
2. Turn the static scripts into ES modules (`<script type="module">`) that import what they use instead of reading globals.
3. Split the drill into a pure state machine, `step(drill, { active, conds, live, paused }, now) -> events`, and a renderer that draws a drill state and plays beeps and speech for the events. The hold/rep/timeout cases from the harness become tests: a wobble within the grace period, a broken hold, reps, a rep timeout, a movement-only pose forced to reps, and learn's targets.
4. Pass `info` into the figure solver explicitly, so it can be tested with the real `FEATURE_INFO` dumped from Python.

## Acceptance
- `npm test` (or `node --test tests/js`) runs without a browser and covers the drill's hold/rep logic and `solveFigure` on every built-in preset (no unmet conditions, no foot below the ground, no fold except where a preset needs one).
- No static script reads another script's variables through globals.
