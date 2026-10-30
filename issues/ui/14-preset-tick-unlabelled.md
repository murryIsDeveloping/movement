# 14 · The tick box on each preset card has no label

**Severity:** low · **Size:** small

## Problem
Every preset card in the library starts with a bare checkbox in front of its name. Its purpose ("tick presets, then + group from ticked") is only in a tooltip, and the matching **+ group from ticked** button only appears after you tick one. With 51 presets the boxes look like an enable/disable switch, which is what the checkbox on the pose cards next to it means (**enabled**).

## Where
- `static/library.js:308`: the `.pick` checkbox.
- `static/library.js:242`: the ticked-presets bar.

## Fix
Show the multi-select's purpose up front: a quiet **select to group** toggle in the Presets bar. While it's on, the checkboxes appear and the **N ticked · + group from ticked · cancel** bar stays visible. While it's off, there are no checkboxes.

## Acceptance
- No unlabelled checkboxes in the library by default.
- Making a group from several presets is discoverable from the Presets bar.
