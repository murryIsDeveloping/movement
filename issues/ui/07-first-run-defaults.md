# 07 · First run starts from untuned defaults

**Severity:** medium · **Size:** small

## Problem
A new install starts with the four hard-coded poses in `DEFAULT`. They have no `preset` link, so every card shows **not in library**. Their values are also rougher than the tested built-ins: the default jog is `step_cadence > 1.0`, while the tested preset uses 0.4 plus lean limits. Nothing on screen points a new user to the library or its game groups.

## Where
- `src/config.py:12-25`: `DEFAULT["poses"]`.
- `static/index.html:155-157`: the only guidance above the poses.

## Fix
Pick one:
1. **Defaults from the library.** On first run, build `poses` from a built-in group (for example *mmo hunter*), server-side in `src/library.py`. Map presets to poses the same way `poseFromPreset` does in `static/library.js:50`. The cards are then linked to the library and tested.
2. **A hint.** While the poses still equal `DEFAULT`, show one line above them: "New here? Load a ready-made setup from the **library**", with a button that opens the library panel.

Option 1 is better for the player. Option 2 is the smallest change.

## Acceptance
- With an empty config folder, the first launch shows tested poses linked to the library, or a clear pointer to them.
