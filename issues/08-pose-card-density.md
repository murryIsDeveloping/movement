# 08 · Pose cards are dense and jargon is unexplained

**Severity:** medium · **Size:** medium

## Problem
- The card header packs 12 controls into one row: ↑, ↓, name, key, hold, delay, badge, enabled, + condition, capture, → library and delete. In the 640 px column it wraps unpredictably, and the important parts (name, key, on/off) don't stand out.
- Feature names in conditions are raw `snake_case`, like `hip_drop` and `right_arm_raise`. The only description is a tooltip on the dropdown.
- Values have no units, although the page says they're in "torso lengths or degrees".

## Where
- `static/index.html:268-280`: the card header.
- `static/index.html:323-330`: the condition row; its grid is at `:41`.
- `src/features.py`: `FEATURE_INFO` holds each feature's description and range. A unit may need adding there.

## Fix
1. Split the header into two rows:
   - Row 1: name, key, enabled and the badge.
   - Row 2, smaller and dimmer: hold, delay, ↑↓, + condition, capture, → library and delete.
2. Show each feature's `desc` as small dim text under its condition row. Optionally show friendlier labels in the dropdown, like "right arm raise", while keeping the feature name as the value.
3. Add a `unit` (`"°"` or `"t"`) to `FEATURE_INFO` in Python, which DECISIONS.md keeps as the source for feature info. Append it to the live value and the number input, as `92°` or `0.31 t`. Explain `t` once in the help text: "t = torso lengths".
4. Check the layout at 640 px and at the 900 px breakpoint where the page becomes one column.

## Acceptance
- At 640 px, each card's header is two tidy rows, with the name and key most prominent.
- Every condition shows what its feature means and its unit without hovering.
