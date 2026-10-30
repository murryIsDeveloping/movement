# 02 · What the app knows about each feature is spread across five places

**Severity:** medium · **Size:** medium · **Related:** [01](01-browser-code-untestable.md), [03](03-recordings-lack-landmarks.md)

## Problem
Adding a feature (like `knee_angle` and `knee_out`) means editing five separate places that each describe part of it, with nothing checking they agree:

| What | Where |
|------|-------|
| description, unit, range | `src/features.py:10` `FEATURES` |
| body part (for the figure's highlights and clash grouping) | `static/figure.js:15` `FIG_PARTS`, `:19` `figParts`, `:255` `clashGroups`, matched on name strings like `left_` and `knee` |
| motion or position | `static/figure.js:131` `FIG_STILL`, `:206` `motionArrows`, `static/drill.js:56` `COACH_MOVES`, a regex on names |
| coaching phrases | `static/drill.js:33` `COACH` |
| the formula itself | `src/features.py` and again in `static/figure.js:56` `figFeatures` ("change one, change both", `src/features.py:102`) |

The hold-vs-reps decision (`needsMotion`, `static/drill.js:102`) depends on "is this a motion feature?", which only the regex knows. A new motion feature that the regex misses would quietly be treated as holdable. The only cross-check is a test that `FIG_MARGIN` lists every unit (`tests/test_features.py:33`). Whether a motion is one you keep going (held for seconds, like jog) or a burst (counted in reps, like jump) is a further hardcoded name: `sustained` in `static/drill.js:105` checks for `step_cadence`.

## Fix
1. Give each entry in `FEATURES` all of its metadata: `part` (`armL`, `armR`, `legL`, `legR`, `torso`, `head`, `both arms`), `kind` (`position`, `motion`, `sustained` motion or `baseline`), and `cue` (what to say when it needs to go up, and down). `FEATURE_INFO` already reaches the GUI, so these come along for free.
2. Replace `FIG_PARTS`/`figParts`/`clashGroups`, `FIG_STILL`, `COACH_MOVES` and `COACH` with lookups in `info`.
3. Add a parity test: feed the same body positions through `FeatureEngine` and the figure's `figFeatures` and check the static features agree (needs [01](01-browser-code-untestable.md)'s JS test runner). The Python side can dump fixture joints and expected values to JSON for the JS test to read.

## Acceptance
- Adding a feature touches `src/features.py` (entry and formula) and `figFeatures` only, and a test fails if the two formulas disagree.
- No JS file decides a feature's part, kind or cue from its name.
