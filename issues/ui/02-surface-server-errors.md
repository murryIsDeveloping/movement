# 02 · Accessibility and rejected edits never reach the GUI

**Severity:** high (trust) · **Size:** small

## Problem
Two failures are only printed to the console, and the packaged app has no console:
- **Accessibility not granted (macOS).** Keys never reach the game. The user ticks send keys and plays, nothing happens, and nothing explains why.
- **Config rejected by the server.** The server drops the edit. After the 2-second `pending` window the page takes the server's poses back, so the user's edit silently reverts.

## Where
- `app.py:111-112`: the `accessibility_trusted()` result is only printed.
- `src/server.py:126-128`: `config rejected` is only printed.
- `static/index.html:201-206`: the page re-syncs from the server, which reverts the local edit with no message.

## Fix
1. Store the trust result on `App` as `self.trusted`, and add `"trusted": self.trusted` to the state published at `app.py:92-95`. If `accessibility_trusted(prompt=False)` is cheap, recheck it every few seconds, so granting permission mid-session clears the warning without a restart.
2. In the page, when `send_keys` is on and `trusted === false`, show a red pill next to the toggle: **keys blocked: grant Accessibility to Movement**. Give it the title "System Settings › Privacy & Security › Accessibility". On Windows, `trusted` is always true.
3. When a config is rejected, send the error back on that socket as `{"type": "error", "error": str(e)}`. Show it as a dismissable red line above `#poses`, and clear it on the next accepted save.

## Acceptance
- In the packaged macOS app without Accessibility permission, the red pill appears as soon as send keys is ticked.
- A rejected edit shows its reason on the page. The console print can stay.
