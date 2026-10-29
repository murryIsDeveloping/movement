---
name: clean-review
description: Review code for long-term cleanliness - readability, maintainability, duplication and simplicity - not bugs. Use when asked to review code health, tidiness or maintainability, or run /clean-review. Takes an optional target - a path, "all" for the whole repo, or nothing for the uncommitted diff plus the last commit.
---

# Clean review

Review for how easy this codebase will be to live with in a year. Bugs are out of scope unless one is obvious; mention it in a single line and move on.

## Scope

- No argument: `git diff HEAD` plus `git show HEAD`. Read the whole of each touched file, not only the hunks, since duplication and drift show up across a file.
- A path: that file or directory.
- `all`: the whole repo (`app.py`, `build.py`, `src/`, `static/`, `tests/`).

Read `DECISIONS.md` first. Don't flag anything that a decision there deliberately chose.

## What to look for

**Readability**
- Names that don't say what a thing is or its unit (torso units, degrees, steps/s). Units matter everywhere in this codebase.
- Functions doing several jobs, deep nesting, clever one-liners that need a second read.
- Comments that restate code, or missing comments where the *why* is non-obvious (mirroring, baselines, MediaPipe quirks).

**Duplication**
- Logic repeated across Python and JS. Known hotspot: `static/figure.js` re-implements feature formulas from `src/features.py` for the stick figure (`figFeatures`). Check they still agree, and flag new copies. Unit ranges come from Python (`UNIT_RANGES`); keep it that way.
- Left/right copy-paste that should be one function looped over sides.
- Constants (ports, thresholds, ranges, paths) defined in more than one place.

**Simplicity**
- Abstractions, options or config with one caller or no current use.
- Code that could be deleted: dead branches, unused features, stale workarounds.
- State that's threaded around when it could be derived.

**Long-term maintenance**
- `static/` growth: when a section of `index.html` or a JS file is big and self-contained enough to pull into its own file, say so.
- Hidden coupling: config keys, feature names or WebSocket message shapes that must match between `src/server.py`, `app.py` and the page with nothing enforcing it.
- Cross-platform branches (macOS/Windows) that are untested or drift apart.
- Tests: behavior in `src/` with no test, or tests coupled to internals so every refactor breaks them.

## Judgement

- Only report what would really pay off. Five sharp findings beat twenty nits. Skip pure style preferences.
- Match the existing style: dense, short comments, compact code. Don't push toward more layers, classes or boilerplate.
- A small amount of duplication is fine when sharing would add more machinery than it saves. Say so when you choose to leave it.

## Output

A ranked list, highest payoff first. For each item:
- `file_path:line`, plus a one-line title
- What's wrong and what it will cost later (one or two sentences)
- The concrete change, with a short snippet if it helps
- Size: small / medium / large

End with one line on overall health and the single change you'd make first. Don't edit files unless the user asks you to apply findings.
