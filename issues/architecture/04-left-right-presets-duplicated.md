# 04 · Every left/right pose is written out twice

**Severity:** low · **Size:** small · **Related:** none

## Problem
Most built-in presets come in left and right pairs (30 of them in `presets.yaml`: punches, swipes, uppercuts, knee lifts, diagonals, tree, crescent, warrior II…). Each pair is hand-copied, with every `left_`/`right_` swapped and the sign of `lean`, `head_tilt` and the sideways speeds flipped. Tuning one side means remembering to edit the other the same way, and a slip is hard to spot in YAML.

## Where
- `presets.yaml`: the pairs, e.g. `tree right` / `tree left`, `warrior 2 right` / `warrior 2 left`.
- `src/library.py`: loads presets and groups; the natural place to expand a mirrored preset.

## Fix
1. Allow `mirror: <name of the other side>` on a preset. On load, the library generates the mirrored preset with `left_`↔`right_` swapped in feature names and in its notes, and `lean`, `head_tilt` and `*_wrist_vx` conditions flipped (`>` v becomes `<` -v). A group can list either side.
2. Tuning the original saves only the original; the mirror follows. Cloning a mirrored built-in clones both sides.
3. Convert the existing pairs, checking each generated side against the hand-written one before deleting it.

## Acceptance
- A test mirrors each converted preset and gets the old hand-written other side back (same conditions, keys aside).
- `presets.yaml` holds each pair once.
