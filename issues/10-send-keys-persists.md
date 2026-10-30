# 10 · Send keys stays on after a restart

**Severity:** low-medium · **Size:** small · **Related:** [03](03-send-keys-state-unclear.md)

## Problem
`send_keys` is saved to `config.yaml` with every edit. If the user quits with keys on, the next launch sends keys as soon as it sees a body, into whatever window has focus: the browser that's opening, a terminal, and so on. The README calls send keys "off by default", but that's only true for a fresh config.

## Where
- `app.py:44-51`: `set_config` merges and saves the whole config, `send_keys` included.
- `src/config.py:16`: the default is `False`.

## Fix
Keep send keys for the current session only:
- Store `send_keys` in memory on `App`, and remove it from the config before `cfgmod.save`.
- On load, force it to false, ignoring any value already in an existing `config.yaml`.
- Leave it out of exports too.

Update the README if its wording needs to change.

## Acceptance
- Quitting with keys on and relaunching starts with keys off.
- A test shows `set_config({"send_keys": True})` doesn't write `send_keys: true` to disk.
