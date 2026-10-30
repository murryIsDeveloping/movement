# 13 · Drill setup shows hold and reps whatever "positions" is set to

**Severity:** low · **Size:** small

## Problem
The drill setup lists **positions** (hold / reps), then **hold** and **reps** together. Which one applies to which pose is only in the tooltips: with positions on *reps*, hold still matters for poses you keep going (jog), and reps still matters for motion poses (jump, punch). A first-time user sees two numbers and can't tell which one they're setting. **reps** also has no unit while every other row has one.

## Where
- `static/index.html:284-286`: the positions, hold and reps rows.

## Fix
Put a one-line hint under the two rows that changes with **positions**:
- hold: "Positions held 5 s · jumps and punches done 5 times · jog kept up 5 s"
- reps: "Positions and jumps done 5 times · jog kept up 5 s"

Build it from the current values, and give **reps** the unit "×".

## Acceptance
- Without hovering, the user can tell what each number will do in the drill.
