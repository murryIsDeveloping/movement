"""Preset library: named poses with a tested/untested status, and groups of them to load as the active poses.

A group is a setup for one game or class (WoW hunter, Mario...): its presets plus its own key for each, overriding
the preset's default key, since the same jump is space in one game and z in another.

Built-in presets and groups ship with the app in presets.yaml and are read-only, so they can't be broken: users
build on them with their own presets (often clones of built-ins) and groups in my_presets.yaml, next to config.yaml.
Running from source, built-ins are editable too: that is how they get tuned before shipping.
"""
from pathlib import Path

import yaml

from src import paths
from src.keys import valid_key
from src.rules import Pose

BUILTIN = paths.resource_root() / "presets.yaml"
USER = paths.config_path().parent / "my_presets.yaml"
STATUSES = ("tested", "untested")


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write(lib: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(lib, f, sort_keys=False, allow_unicode=True)


def _merge(builtin: dict, user: dict) -> dict:
    tag = lambda d, key, b: [{**x, "builtin": b} for x in d.get(key) or []]
    return validate({key: tag(builtin, key, True) + tag(user, key, False) for key in ("presets", "groups")})


def _part(lib: dict, builtin: bool) -> dict:
    """The built-in or user half of a library, without the builtin flags, as stored on disk."""
    return {key: [{k: v for k, v in x.items() if k != "builtin"} for x in lib[key] if x["builtin"] == builtin]
            for key in ("presets", "groups")}


def load(builtin: Path | None = None, user: Path | None = None) -> dict:
    """Built-ins then the user's own, each preset and group flagged builtin true/false.

    A new build's built-ins can disagree with the user's file: a user preset or group sharing a new built-in's name
    is renamed "<name> (mine)", and group members naming a preset that no longer exists are dropped.
    Keys pynput can't press (older builds saved any text) are repaired: a preset's resets to "1", a group's is dropped."""
    b, u = _read(builtin or BUILTIN), _read(user or USER)
    for p in (b.get("presets") or []) + (u.get("presets") or []):
        if not valid_key(str(p.get("key", ""))):
            print(f"library: preset {p['name']!r}: unknown key {p.get('key')!r}, reset to '1'")
            p["key"] = "1"
    for g in (b.get("groups") or []) + (u.get("groups") or []):
        for m, k in list((g.get("keys") or {}).items()):
            if str(k).strip() and not valid_key(str(k)):
                print(f"library: group {g['name']!r}: unknown key {k!r} for {m!r}, dropped")
                del g["keys"][m]
    for key in ("presets", "groups"):
        taken = {x["name"] for x in b.get(key) or []}
        for x in u.get(key) or []:
            if x["name"] in taken:
                old, x["name"] = x["name"], f"{x['name']} (mine)"
                if key == "presets":
                    for g in u.get("groups") or []:
                        g["presets"] = [x["name"] if m == old else m for m in g.get("presets") or []]
                        g["keys"] = {x["name"] if m == old else m: k for m, k in (g.get("keys") or {}).items()}
            taken.add(x["name"])
    known = {p["name"] for p in (b.get("presets") or []) + (u.get("presets") or [])}
    for g in u.get("groups") or []:
        g["presets"] = [m for m in g.get("presets") or [] if m in known]
    return _merge(b, u)


def save(lib: dict, edit_builtins: bool, builtin: Path | None = None, user: Path | None = None) -> dict:
    """Saves the user's half. Built-ins come from disk unless edit_builtins, so a client can't change them.
    Raises ValueError like validate, e.g. a user preset taking a built-in's name."""
    builtin, user = builtin or BUILTIN, user or USER
    lib = validate(lib)
    lib = _merge(_part(lib, True) if edit_builtins else _read(builtin), _part(lib, False))
    if edit_builtins:
        _write(_part(lib, True), builtin)
    _write(_part(lib, False), user)
    return lib


def validate(lib: dict) -> dict:
    """Normalised copy, or ValueError: a bad pose, a duplicate name, an unknown status, a group naming a missing
    preset or binding a key pynput can't press, or a built-in group naming a user preset (built-ins must stand alone)."""
    presets, builtins = [], {}
    for d in lib.get("presets") or []:
        pose = Pose.from_dict(d).to_dict()
        pose.pop("preset")   # only active poses link back to a preset
        name = pose.pop("name")
        if name in builtins:
            raise ValueError(f"two presets named {name!r}")
        status = d.get("status", "untested")
        if status not in STATUSES:
            raise ValueError(f"preset {name!r}: status must be one of {STATUSES}, got {status!r}")
        builtins[name] = bool(d.get("builtin", False))
        presets.append({"name": name, "status": status, "notes": str(d.get("notes", "")), **pose, "builtin": builtins[name]})
    groups, gnames = [], set()
    for g in lib.get("groups") or []:
        if g["name"] in gnames:
            raise ValueError(f"two groups named {g['name']!r}")
        gnames.add(g["name"])
        builtin = bool(g.get("builtin", False))
        members = list(g.get("presets") or [])
        for m in members:
            if m not in builtins:
                raise ValueError(f"group {g['name']!r}: no preset named {m!r}")
            if builtin and not builtins[m]:
                raise ValueError(f"built-in group {g['name']!r} names your preset {m!r}")
        keys = {m: str(k) for m, k in (g.get("keys") or {}).items() if m in members and str(k).strip()}   # stale keys dropped
        for m, k in keys.items():
            if not valid_key(k):
                raise ValueError(f"group {g['name']!r}: unknown key {k!r} for {m!r}")
        groups.append({"name": g["name"], "notes": str(g.get("notes", "")), "presets": members, "keys": keys, "builtin": builtin})
    return {"presets": presets, "groups": groups}
