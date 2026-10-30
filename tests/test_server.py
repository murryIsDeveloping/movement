from src import server
from src.server import Hub, make_app


def routes(app):
    return {(r.method, r.resource.canonical) for r in app.router.routes()}


def test_recording_only_when_running_from_source(monkeypatch):
    monkeypatch.setattr(server, "DEV", True)
    assert ("POST", "/recording") in routes(make_app(Hub()))
    monkeypatch.setattr(server, "DEV", False)   # packaged app: drills aren't recorded
    assert ("POST", "/recording") not in routes(make_app(Hub()))


def test_packaged_app_batches_no_frames(monkeypatch):
    monkeypatch.setattr(server, "DEV", False)
    hub = Hub()
    hub.publish(None, {"t": 1.0, "body": True, "paused": False, "missing": [], "features": {}, "state": []})
    assert '"frames": []' in hub.take()
