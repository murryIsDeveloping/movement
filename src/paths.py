"""Where resources and user config live, in dev vs packaged app."""
import os
import sys
from pathlib import Path

APP_NAME = "Movement"


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    if frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _user_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def data_dir() -> Path:
    d = _user_data_dir() / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    if not frozen():
        return resource_root() / "config.yaml"
    return data_dir() / "config.yaml"


def setup_frozen_env() -> None:
    """Packaged app has no terminal: log to a file, and keep matplotlib's font cache out of the read-only bundle."""
    if not frozen():
        return
    d = data_dir()
    os.environ.setdefault("MPLCONFIGDIR", str(d / "matplotlib"))
    log = open(d / "movement.log", "a", buffering=1)
    sys.stdout = sys.stderr = log
