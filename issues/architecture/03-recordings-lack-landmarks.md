# 03 · Recordings can't replay a feature change

**Severity:** medium (blocks checking tuning work against real sessions) · **Size:** small · **Related:** [02](02-feature-metadata-scattered.md)

## Problem
Drill and learn recordings save each frame's computed features and active poses, not the body joints they came from. A change to the rules (a threshold, a new condition) can be replayed through `RuleEngine` against a real session, but a change to `FeatureEngine` can't: there is nothing to recompute the features from.

The hold fix (baselines that crawl while a pose is held) and knee angle could only be tested on synthetic bodies from `tests/fixtures.py`, so their effect on the tested poses (jog in particular) is unknown until the next live drill.

## Where
- `src/server.py:38-39`: `Hub.publish` appends `t`, `body`, `paused`, `missing`, `f` (features) and the pose state per frame.
- `app.py:86-92`: the landmarks `p` exist here, but only `feats` reach `hub.publish` (`app.py:107`).

## Fix
1. Publish the body joints with each frame while running from source: the 13 `BODY` joints from `src/landmarks.py` as `[x, y, visibility]`, rounded to 4 places. Keep it gated on `DEV`, like recording itself (`src/server.py:16`); the packaged app never stores them.
2. Save them in the recording's frames as `j`.
3. Add a small dev script, `python -m tools.replay recordings/<file>.json`, that runs the frames' joints through the current `FeatureEngine` and `RuleEngine` and prints, per prompt, when each pose fired before and after. That is the check to run after any feature or threshold change.

## Acceptance
- A new recording holds joints for every frame, and its size grows by no more than about 2x.
- Replaying an old recording (no `j`) explains that it can only replay rules, not features.
- Replaying a new one through unchanged code reproduces its recorded features exactly.
