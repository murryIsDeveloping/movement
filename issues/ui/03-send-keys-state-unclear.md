# 03 · Held keys look the same whether sent or not

**Severity:** high (trust) · **Size:** small · **Related:** [09](09-drill-send-state.md), [10](10-send-keys-persists.md)

## Problem
The big green key chips under the preview (`#held`) show the keys the poses want, whether or not they're being sent. With send keys off they look exactly like real presses, so the user may believe keys are reaching the game. The toggle itself is a small checkbox inside a pill, which is easy to miss from 2–3 m.

## Where
- `static/index.html:216`: `#held` is rendered from `m.held` whatever `m.send_keys` is.
- `static/index.html:30-31`: the `.held` styles.
- `static/index.html:134`: the toggle.

## Fix
1. When `send_keys` is false, show the chips greyed out and struck through, with a small "not sent" label. Add a `.held.off` class with a `--off` background and `text-decoration:line-through`.
2. Replace the checkbox pill with a large two-state button: **KEYS ON** in solid `--on` and bold, or **keys off** with a grey outline. If it's simpler for the existing `pushConfig` wiring, keep the checkbox hidden behind it.
3. Optionally, tint the preview's border green while keys are on, so the state can be seen from across the room.

## Acceptance
- From 2–3 m you can tell at a glance whether keys are on or off.
- With keys off, the held chips can't be mistaken for real presses.
