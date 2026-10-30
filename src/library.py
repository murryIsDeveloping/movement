"""Preset library: named poses with notes on how to do them, and groups of them to load as the active poses.

A group is a setup for one game or class (MMO hunter, platformer...): its presets plus its own key for each, overriding
the preset's default key, since the same jump is space in one game and z in another.

Built-in presets and groups ship with the app in presets.yaml and are read-only, so they can't be broken: users
build on them with their own presets (often clones of built-ins) and groups in my_presets.yaml, next to config.yaml.
Running from source, built-ins are editable too: that is how they get tuned before shipping. Built-in presets are
never deleted or renamed though, only tuned or cloned.

A left/right pair is stored once: the preset written out carries `mirror: {name, key}`, and loading generates the
other side (flagged mirror_of) with left and right swapped and sideways signs flipped. Tuning either side tunes both.
"""
import re
from pathlib import Path

import yaml

from src import paths
from src.keys import valid_key
from src.rules import Pose

BUILTIN = paths.resource_root() / "presets.yaml"
USER = paths.config_path().parent / "my_presets.yaml"
MIRRORED = ("notes", "conditions", "margin", "enabled", "hold", "delay")   # shared by both sides of a pair
SIDEWAYS = re.compile(r"^(lean|head_tilt|(left|right)_wrist_vx)$")   # + is image right, so mirroring flips the sign
_SIDE = re.compile(r"(?<![A-Za-z])(left|right|Left|Right)(?![A-Za-z])")


def _swap(s: str) -> str:
    """left <-> right, in names, notes and feature names."""
    return _SIDE.sub(lambda m: {"left": "right", "right": "left", "Left": "Right", "Right": "Left"}[m.group(1)], s)


def _mirror_condition(c: dict) -> dict:
    f = _swap(c["feature"])
    if SIDEWAYS.match(f):   # lean > 0.25 becomes lean < -0.25
        return {"feature": f, "op": {">": "<", "<": ">"}[c["op"]], "value": -float(c["value"]) + 0.0}
    return {**c, "feature": f}


def _mirror(p: dict) -> dict:
    """The other side of a preset: the fields both share, mirrored."""
    return {"notes": _swap(str(p.get("notes", ""))), "conditions": [_mirror_condition(c) for c in p.get("conditions") or []],
            **{k: p[k] for k in MIRRORED if k in p and k not in ("notes", "conditions")}}


def _expand(half: dict) -> dict:
    """Disk form to library form: each mirror: {name, key} becomes its own preset, right after the original."""
    presets = []
    for p in half.get("presets") or []:
        p = dict(p)
        m = p.pop("mirror", None)
        presets.append(p)
        if m:
            presets.append({"name": m["name"], "key": m.get("key", p.get("key")), **_mirror(p), "mirror_of": p["name"]})
    return {**half, "presets": presets}


def _collapse(half: dict, path: Path) -> dict:
    """Library form back to disk form: each generated side folds into its original as mirror: {name, key}. If the
    generated side was tuned since path was saved, its tuning goes into the original; if its original is gone, it
    stands alone."""
    try:
        old = {p["name"]: p for p in validate(_expand(_read(path)))["presets"]}
    except (ValueError, KeyError):
        old = {}
    shared = lambda p: {k: p.get(k) for k in MIRRORED}
    names = {p["name"] for p in half["presets"] if not p.get("mirror_of")}
    out = {p["name"]: {k: v for k, v in p.items() if k != "mirror_of"} for p in half["presets"]
           if p.get("mirror_of") not in names}
    for g in half["presets"]:
        if g.get("mirror_of") in names:
            o = out[g["mirror_of"]]
            if g["name"] in old and shared(g) != shared(old[g["name"]]):
                o.update(_mirror(g))
            o["mirror"] = {"name": g["name"], "key": g["key"]}
    return {**half, "presets": list(out.values())}


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
    b, u = _expand(_read(builtin or BUILTIN)), _expand(_read(user or USER))
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
                    for p in u.get("presets") or []:
                        if p.get("mirror_of") == old:
                            p["mirror_of"] = x["name"]
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
    Raises ValueError like validate, e.g. a user preset taking a built-in's name, or when edit_builtins drops or
    renames a built-in preset."""
    builtin, user = builtin or BUILTIN, user or USER
    if edit_builtins:   # before validate, which would only complain about a group naming the missing preset
        kept = {p["name"] for p in lib.get("presets") or [] if p.get("builtin")}
        missing = [p["name"] for p in _expand(_read(builtin))["presets"] if p["name"] not in kept]
        if missing:
            raise ValueError(f"built-in presets can't be deleted or renamed: {', '.join(missing)}")
    lib = validate(lib)
    b = _collapse(_part(lib, True), builtin) if edit_builtins else _read(builtin)
    u = _collapse(_part(lib, False), user)
    lib = _merge(_expand(b), _expand(u))
    if edit_builtins:
        _write(b, builtin)
    _write(u, user)
    return lib


def group_poses(group: str, builtin: Path | None = None) -> list[dict]:
    """A built-in group as active poses, linked to their presets: the same mapping as poseFromPreset in library.js.
    KeyError if there's no such group, ValueError like validate."""
    lib = validate(_expand(_read(builtin or BUILTIN)))
    g = next((g for g in lib["groups"] if g["name"] == group), None)
    if g is None:
        raise KeyError(f"no built-in group named {group!r}")
    presets = {p["name"]: p for p in lib["presets"]}
    return [{"name": m, "key": g["keys"].get(m) or presets[m]["key"],
             **{k: presets[m][k] for k in ("conditions", "margin", "enabled", "hold", "delay")}, "preset": m}
            for m in g["presets"]]


def validate(lib: dict) -> dict:
    """Normalised copy, or ValueError: a bad pose, a duplicate name, a group naming a missing preset or binding a key
    pynput can't press, or a built-in group naming a user preset (built-ins must stand alone). A status (tested or
    untested, which older builds kept) is dropped, so the next save drops it from the file too."""
    presets, builtins = [], {}
    for d in lib.get("presets") or []:
        pose = Pose.from_dict(d).to_dict()
        pose.pop("preset")   # only active poses link back to a preset
        name = pose.pop("name")
        if name in builtins:
            raise ValueError(f"two presets named {name!r}")
        builtins[name] = bool(d.get("builtin", False))
        mirror = {"mirror_of": str(d["mirror_of"])} if d.get("mirror_of") else {}
        presets.append({"name": name, "notes": str(d.get("notes", "")), **pose, **mirror, "builtin": builtins[name]})
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
