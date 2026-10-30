# 09 · The drill doesn't show send-keys state

**Severity:** low-medium · **Size:** small · **Related:** [03](03-send-keys-state-unclear.md)

## Problem
The drill covers the whole page, which hides the send toggle. If keys are on, poses send `space`, `w` and so on into the focused browser tab, where space scrolls the page behind the drill. If keys are off, the user can't confirm that from the drill screen.

## Where
- `static/drill.js:6-19`: `startDrill`.
- `static/index.html:169`: `.drill-head`.

## Fix
1. Show a tag in `.drill-head`: **keys on** in green or **keys off** in grey, updated from the latest `send_keys`.
2. Optionally, turn sending off for the drill by pushing `send_keys: false` with `pushConfig`, and restore the previous value in `endDrill`. If you do this, mention it in the README's drill section.

## Acceptance
- The drill screen always shows whether keys are being sent.
