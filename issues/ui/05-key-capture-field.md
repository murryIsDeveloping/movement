# 05 · The key field expects pynput names

**Severity:** medium · **Size:** small · **Related:** [01](01-bad-key-crashes-camera.md)

## Problem
The key field's only help is a tooltip: "pynput key name: a, 1, space, shift, f1 ...". Users don't know pynput's names (is it `page_up`? `ctrl_l`? `esc`?), and a wrong guess leads straight to issue 01.

## Where
- `static/index.html:272`: the key input on pose cards.
- `static/library.js:270`: a preset's default key.
- `static/library.js:233`: the key chips in groups (`input.gk`).

## Fix
1. Add a shared helper, `wireKeyInput(input, onSet)`, in `index.html` or a small new file next to `figure.js`. On focus it sets the placeholder to "press a key…". On `keydown` it calls `preventDefault`, maps `e.key` to the pynput name and calls `onSet`. Typing a name and pressing Enter still works, for keys the browser can't capture.
2. Map keys like this:
   - a single printable character → that character, lowercased
   - `' '` → `space`, `Enter` → `enter`, `Tab` → `tab`, `Escape` → `esc`, `Backspace` → `backspace`
   - `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight` → `up`, `down`, `left`, `right`
   - `F1` to `F12` → `f1` to `f12`
   - `Shift`, `Control` and `Alt`, using `e.location` → `shift_l`/`shift_r`, `ctrl_l`/`ctrl_r`, `alt_l`/`alt_r`
   - `PageUp`, `PageDown`, `Home`, `End`, `Insert`, `Delete` → `page_up`, `page_down`, `home`, `end`, `insert`, `delete`
3. Use the helper in all three places. While a key input has focus, Escape must not also close the panels (`index.html:249`).

## Acceptance
- Clicking the field and pressing space sets `space`. F1 sets `f1`. Left shift sets `shift_l`.
- Every value the helper produces passes the server-side check from issue 01.
