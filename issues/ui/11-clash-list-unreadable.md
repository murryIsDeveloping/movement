# 11 · The clash list is long and written in feature code

**Severity:** medium · **Size:** medium

## Problem
With the *workout* group active, the header button reads **clashes (37)** in warning amber, permanently. Opening it gives 37 cards like "**star jump** (p) and **squat hands out** (6) both fire when `hip_rise > 0.2, left_wrist_up > 0.5, right_wrist_up > 0.5, hip_drop > 0.4, 65 < right_arm_raise < 106, …`". The user can't tell which clashes matter (ones that will really misfire in play) from ones that are harmless or deliberate, and the conditions are raw feature names rather than the words used on the pose cards ("hip rise", "lean"). A warning that's always on gets ignored, so the one clash that matters is missed.

## Where
- `static/figure.js:342-362`: `drawClashList`, the card text.
- `static/figure.js:335-336`: the button count and amber state.

## Fix
1. Write conditions as the pose cards do: `f.replace(/_/g, ' ')` and `fmtU` units (`hip rise > 0.2 t`), one per line rather than a comma run.
2. Sort the worst first: `same` and `b-in-a`/`a-in-b` (one pose always fires the other) above partial overlaps.
3. Let a clash be marked "fine" (stored by pose-name pair in the config), dimmed and not counted. The button then counts only unreviewed clashes, so amber means "something new to look at".

## Acceptance
- A clash card reads in the same words as the pose cards.
- Always-together clashes are at the top.
- A group whose clashes have all been reviewed shows a plain **clashes** button, not amber.
