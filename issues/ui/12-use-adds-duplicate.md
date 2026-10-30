# 12 · "use" on a preset already in the active poses adds a second copy

**Severity:** medium · **Size:** small

## Problem
In the library, a preset that's already active shows **use** next to "in active poses". Clicking it anyway appends a second copy of the pose with the same key, so the key now has two poses behind it, and the pose list gets longer for no visible reason. The label suggests the user already has it, but the button still looks like the next step.

## Where
- `static/library.js:321`: the `use` button and "in active poses" note.
- `static/library.js:52-64`: `usePresets` appends without checking.

## Fix
When `inUse.has(pr.name)`, replace **use** with a quiet **show** button that closes the library and scrolls to that pose card (flash its border). Keep a way to add a second copy only if that's wanted: **use again**, as a plain button with the title "adds another copy, e.g. to bind it to a second key".

## Acceptance
- One click on an active preset never silently duplicates it.
- From the library you can jump to the active pose to tune it.
