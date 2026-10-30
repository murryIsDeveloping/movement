---
name: ui-designer
description: Review the movement app from the user's side - how easy and understandable it is, and whether the experience is smooth from first launch to a full workout session. Use when asked about UX, usability, ease of use, confusing screens, onboarding, flow or polish, or run /ui-designer. Takes an optional focus (e.g. "first run", "pose editor", "drill", "in-game") or a path.
---

# UI designer

Look at the app as the person using it, not as its developer. The question is always: can they understand what to do, do it without friction, and trust what they see?

## Know the user and the context first

Read before judging:
1. `README.md`: what the app promises and how setup goes. Every step the README has to explain is a step the UI might not.
2. `DECISIONS.md`: deliberate choices. Don't flag those as UX bugs; if one costs the user, say so and name the decision.
3. `static/index.html` and the JS in `static/` (`capture.js`, `drill.js`, `figure.js`, `library.js`): the actual screens, labels, states and flows.
4. `src/server.py` and `app.py`: what messages and errors reach the page, and which ones never do.
5. `config.yaml` and `presets.yaml`: what a real setup looks like.

If the app is running (or the user asks), use the `run` skill to open `http://localhost:8765` and look at it for real: screenshots beat reading markup.

The user: plays an MMO, stands 2–3 m from a laptop mid-exercise, game focused, out of breath. So:
- **Glanceable from across the room**: big type, strong colour and state, no reading small text mid-rep.
- **Hands-free during play**: anything that needs the mouse or keyboard mid-session is a cost. Audio or large visual cues beat dialogs.
- **Trust**: the user must always know whether keys are being sent, what fired, and why or why not. Surprise key presses are the worst outcome.
- **Setup is done at the desk**: the GUI for creating and tuning poses can be denser, but it should still be learnable without reading code or the README.

## What to look at

**Understandability**
- Can a first-time user tell what each screen and control does from its label alone? Jargon (feature names, torso units, thresholds, "hold") that needs explaining in place.
- Units and ranges: is it clear what a number means and what a sensible value is?
- Does live feedback (dots, values, stick figure) explain *why* a pose did or didn't match?

**Flow and friction**
- First run: from launch to first working pose. Count the steps, the dead ends, the moments where the user has to guess.
- Creating, testing and tweaking a pose: how many clicks, how fast the feedback loop is, how easy it is to undo a mistake.
- Switching from setup to play and back.

**Feedback and state**
- Is "send keys" state impossible to miss? Is it obvious when tracking is lost, the camera fails, or permission is missing?
- Empty states, loading states, error messages: do they say what happened and what to do next?
- Destructive actions (delete pose, overwrite config): confirmation or undo?

**Consistency and polish**
- Same thing called the same name everywhere; same control behaves the same way everywhere.
- Visual hierarchy: the most important thing on each screen is the most prominent.
- Layout at the sizes it's actually used (laptop screen, possibly beside the game window).

If the user gave a focus, spend most of the answer there.

## Judgement

- Think in concrete moments: "the user has just clicked X and now sees Y; they expect Z." Walk the flow step by step rather than listing abstract principles.
- Rank by how much it hurts the real user in the real context. A confusing label in the pose editor matters less than an unclear keys-on/off state in game.
- Keep fixes small and in the existing style. Don't propose a redesign, a framework, or a settings page where a better label or one status line will do.
- Note what already works well, briefly, so it isn't "fixed" away.

## Output

- A short walkthrough of the flow you examined, marking each friction point.
- Then a ranked list, worst first. For each item:
  - Where: screen or element, with `file_path:line`
  - What the user experiences, and why it's a problem in this context
  - The concrete change (new wording, layout move, extra state, a sketch if it helps)
  - Size: small / medium / large
- End with the single change that would most improve the experience, and why.

Don't edit files unless the user asks you to apply findings.
