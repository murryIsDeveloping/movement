# Issues

One file per issue, in a folder per kind, listed worst first. Each file covers the problem, where it is in the code, the fix, acceptance criteria and size. When an issue is fixed, mark it done in its table.

## Architecture

Structural problems that slowed building coaching, knee features and holds/reps on 2026-10-30. They make later changes harder to check rather than breaking anything now.

| # | Issue | Size | Status |
|---|-------|------|--------|
| 01 | [The browser code can't be tested](architecture/01-browser-code-untestable.md) | medium | open |
| 02 | [What the app knows about each feature is spread across five places](architecture/02-feature-metadata-scattered.md) | medium | open |
| 03 | [Recordings can't replay a feature change](architecture/03-recordings-lack-landmarks.md) | small | open |
| 04 | [Every left/right pose is written out twice](architecture/04-left-right-presets-duplicated.md) | small | done |
| 05 | [Baseline drift is set per frame, not per second](architecture/05-baseline-rates-per-frame.md) | small | done |
| 06 | [The per-frame logic lives inside the camera loop](architecture/06-frame-logic-in-camera-loop.md) | small | open |

Suggested order: 01 and 03 first, since they make every later change checkable (the GUI logic in tests, feature changes against real sessions). 02 builds on 01's test runner. 04 and 05 are small and independent.

## UI

UX issues from a `/ui-designer` review on 2026-10-30.

| # | Issue | Size | Status |
|---|-------|------|--------|
| 01 | [A bad key name crashes the camera loop](ui/01-bad-key-crashes-camera.md) | small | done |
| 02 | [Accessibility and rejected edits never reach the GUI](ui/02-surface-server-errors.md) | small | done |
| 03 | [Held keys look the same whether sent or not](ui/03-send-keys-state-unclear.md) | small | done |
| 04 | [No feedback while the game is focused](ui/04-audio-cues-in-play.md) | small | done |
| 05 | [The key field expects pynput names](ui/05-key-capture-field.md) | small | done |
| 06 | [Deleting a pose has no confirm or undo](ui/06-pose-delete-undo.md) | small | done |
| 07 | [First run starts from untuned defaults](ui/07-first-run-defaults.md) | small | done |
| 08 | [Pose cards are dense and jargon is unexplained](ui/08-pose-card-density.md) | medium | done |
| 09 | [The drill doesn't show send-keys state](ui/09-drill-send-state.md) | small | done |
| 10 | [Send keys stays on after a restart](ui/10-send-keys-persists.md) | small | done |
| 11 | [The clash list is long and written in feature code](ui/11-clash-list-unreadable.md) | medium | open |
| 12 | ["use" on a preset already in the active poses adds a second copy](ui/12-use-adds-duplicate.md) | small | done |
| 13 | [Drill setup shows hold and reps whatever "positions" is set to](ui/13-drill-setup-irrelevant-fields.md) | small | done |
| 14 | [The tick box on each preset card has no label](ui/14-preset-tick-unlabelled.md) | small | open |

11–14 are from a visual-polish pass on 2026-10-30.
