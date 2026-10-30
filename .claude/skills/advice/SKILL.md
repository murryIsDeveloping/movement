---
name: advice
description: Step back and suggest where the movement project should go next - longer-term improvements, quality-of-life for the player and the developer, and code quality direction. Use when asked for advice, ideas, next steps, what to improve, or run /advice. Takes an optional focus area (e.g. "tuning", "packaging", "gameplay").
---

# Advice

Act as a thoughtful collaborator who knows what this project is for, not as a code reviewer.

## Know the project first

Read before advising:
1. `README.md`: what it does and how it's used.
2. `DECISIONS.md`: what was chosen and why. Build on these. Don't re-propose something a decision rejected (for example template matching) unless you have a new reason, and then name the decision you're challenging.
3. `config.yaml`: the poses actually in use. It shows how the app is really played.
4. `git log --oneline -30`: where the momentum is.
5. Skim `src/` and `static/` enough to ground suggestions in real code.

What it is: webcam pose → held keys, so grinding in an MMO becomes a workout. The user stands 2–3 m from a laptop, mid-exercise, with the game focused. That shapes everything:
- Any interaction away from the keyboard is expensive. Hands-free, glanceable, big-text and audio cues win.
- False fires cost more than missed ones (a wrong key in combat), but laggy or unreliable detection kills the workout.
- It's a personal tool, so local-first, simple and low-maintenance beat general or enterprise-grade.

## What to think about

- **Player QoL**: setup friction, calibration, feedback on what fired and why, recovery when tracking is lost, fatigue and session flow, exercise value.
- **Tuning workflow**: making poses faster to create, test and keep clash-free; catching bad thresholds before they bite in game.
- **Developer QoL**: dev loop speed, testability (recorded landmark fixtures, replay), debugging tools, build and packaging pain on both OSes.
- **Code direction**: structural moves that keep the codebase small as features grow, for example where the GUI code should split further, or keeping the Python and JS feature maths from drifting apart.
- **Reliability**: camera and permission failures, key stuck-down safety, focus changes.

If the user gave a focus area, spend most of the answer there.

## Output

- 3–6 suggestions, highest value first. Fewer, better ideas over a long list.
- For each: what it is, why it matters for *this* project (tie it to the use case or a decision), rough effort (small / medium / large), and the first concrete step (with `file_path:line` where relevant).
- Separate quick wins from longer bets if both appear.
- Finish with the one thing you'd do next and why.

Be direct and opinionated. Don't edit files. This skill is for advice; the user decides what to build.
