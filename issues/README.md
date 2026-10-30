# Issues

UX issues from a `/ui-designer` review on 2026-10-30, listed worst first, one file per issue.

Each file covers the problem, where it is in the code, how to reproduce it, the fix, acceptance criteria and size. When an issue is fixed, delete its file or move it to `done/`, and update the table.

| # | Issue | Size | Status |
|---|-------|------|--------|
| 01 | [A bad key name crashes the camera loop](01-bad-key-crashes-camera.md) | small | done |
| 02 | [Accessibility and rejected edits never reach the GUI](02-surface-server-errors.md) | small | done |
| 03 | [Held keys look the same whether sent or not](03-send-keys-state-unclear.md) | small | done |
| 04 | [No feedback while the game is focused](04-audio-cues-in-play.md) | small | done |
| 05 | [The key field expects pynput names](05-key-capture-field.md) | small | done |
| 06 | [Deleting a pose has no confirm or undo](06-pose-delete-undo.md) | small | done |
| 07 | [First run starts from untuned defaults](07-first-run-defaults.md) | small | open |
| 08 | [Pose cards are dense and jargon is unexplained](08-pose-card-density.md) | medium | open |
| 09 | [The drill doesn't show send-keys state](09-drill-send-state.md) | small | open |
| 10 | [Send keys stays on after a restart](10-send-keys-persists.md) | small | open |

Suggested order: do 01 and 05 together, since both touch the key field. Then 02 and 03, which are about trusting what reaches the game. Then the rest.
