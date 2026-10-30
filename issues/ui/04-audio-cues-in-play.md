# 04 · No feedback while the game is focused

**Severity:** medium-high · **Size:** small

## Problem
During play, WoW has focus and the GUI isn't visible. When tracking pauses because the user is out of frame or no body is seen, every key is released silently. The character just stops, and the user can't tell why. Audio cues only exist in the drill and in capture.

## Where
- `static/index.html:208-214`: the pause state is only shown visually.
- `static/capture.js:161-169`: `beep()` and the shared `audio` context, which can be reused.

## Fix
1. In `ws.onmessage`, remember the previous `paused` value. While `send_keys` is on:
   - when tracking pauses, play a low double beep (for example 330 Hz twice);
   - when it resumes, play one high beep (for example 990 Hz).
2. Browsers only allow audio after a user gesture, so create `audio` in the send-keys toggle's click handler, the same way `startDrill` does.
3. Add a small "sound" checkbox next to the toggle, on by default. Remember it in `localStorage`, wrapped in try/catch like `TRIGGER_KEY`.
4. Check that the beeps play while the tab is in the background. Chrome allows audio from an `AudioContext` that has already started.

## Acceptance
- With keys on and WoW focused, walking out of frame and back in gives two distinct beeps.
- There are no beeps when keys are off or the sound box is unticked.
