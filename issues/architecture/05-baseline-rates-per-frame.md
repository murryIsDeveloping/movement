# 05 · Baseline drift is set per frame, not per second

**Severity:** low · **Size:** small · **Related:** [03](03-recordings-lack-landmarks.md)

## Problem
The standing-height baselines for the hips and knees drift by a fixed fraction every frame: `0.01` normally, and `HELD_RATE = 0.0001` while a squat or knee lift is held. So how long a hold lasts, and how fast a posture shift is forgotten, depends on the frame rate. At 30fps a held squat keeps over 90% of its drop after 30s. A slower laptop at 15fps holds twice as long, and a faster camera fades sooner. The tests assume 30fps.

## Where
- `src/features.py:70-73`: `_Baseline(rate=0.01)` and `update(x, rate)`, applied once per call.
- `src/features.py:54`: `HELD_RATE`, documented as per frame.
- `src/features.py:124`, `:141`: the hip and knee baselines pass it.

## Fix
1. Give `_Baseline` a time constant in seconds instead of a per-frame rate, and have `update` take `dt`: `v += (x - v) * (1 - exp(-dt / tau))`. With `tau` around 3.3s it matches today's `0.01` at 30fps; around 330s matches `HELD_RATE`.
2. `FeatureEngine.update` already has `t`; pass the time since the last frame, capped (say at 0.5s) so a stall doesn't jump the baseline.

## Acceptance
- A held squat or knee lift fades at the same speed in seconds at 15, 30 and 60fps (a test runs the same 30s hold at each rate).
- The existing feature tests pass unchanged.
