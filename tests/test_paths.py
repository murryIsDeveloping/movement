import sys
from pathlib import Path

from src import paths


def test_dev_resource_root_is_repo(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.resource_root() == Path(__file__).resolve().parent.parent


def test_dev_config_lives_in_repo(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.config_path() == paths.resource_root() / "config.yaml"


def test_frozen_resource_root_is_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.resource_root() == tmp_path


def test_frozen_config_in_user_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(paths, "_user_data_dir", lambda: tmp_path / "data")
    assert paths.config_path() == tmp_path / "data" / "Movement" / "config.yaml"
    assert (tmp_path / "data" / "Movement").is_dir()
