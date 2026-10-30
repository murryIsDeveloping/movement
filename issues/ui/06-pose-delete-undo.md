# 06 · Deleting a pose has no confirm or undo

**Severity:** medium · **Size:** small

## Problem
**delete** on a pose card removes the pose instantly, and the change saves 300 ms later. A misclick loses the tuned conditions. The library asks before deleting presets and groups (`static/library.js:92`, `:243`), so the two behave differently.

## Where
- `static/index.html:292-295`.

## Fix
- **Preferred: an undo bar.** Keep the removed pose and its index. At the top of `#poses`, show **deleted "jog" · undo** for about 6 seconds. Undo splices the pose back at the same index, then calls `renderPoses()` and `scheduleSave()`.
- **Simpler alternative:** ask with `` confirm(`Delete pose "${p.name}"?`) ``, matching the library's wording.

## Acceptance
- A deleted pose can be restored, or deleting needs confirming.
- Undoing after reordering poses or starting a capture doesn't corrupt `capture.pi`.
