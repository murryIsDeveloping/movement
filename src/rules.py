"""Poses as lists of feature conditions. All true -> key held. Hysteresis per condition."""
from dataclasses import dataclass, field, asdict

from src.features import FEATURES


@dataclass
class Condition:
    feature: str
    op: str          # ">" or "<"
    value: float

    def holds(self, x: float | None, active: bool, margin: float) -> bool:
        if x is None:
            return False
        slack = abs(self.value) * margin if active else 0.0
        if self.op == ">":
            return x > self.value - slack
        return x < self.value + slack


@dataclass
class Pose:
    name: str
    key: str
    conditions: list[Condition] = field(default_factory=list)
    margin: float = 0.1     # fraction of threshold kept as release slack
    enabled: bool = True
    hold: float = 0.0       # seconds the key stays down after the conditions stop: a one-frame punch becomes a press
    delay: float = 0.0      # seconds the conditions must hold before the key goes down: an arm passing through doesn't fire

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Pose":
        """Raises ValueError on an unknown feature or op, so a typo fails on import instead of never firing."""
        conds = []
        for c in d.get("conditions", []):
            if c["feature"] not in FEATURES:
                raise ValueError(f"pose {d['name']!r}: unknown feature {c['feature']!r}")
            if c["op"] not in (">", "<"):
                raise ValueError(f"pose {d['name']!r}: op must be '>' or '<', got {c['op']!r}")
            conds.append(Condition(c["feature"], c["op"], float(c["value"])))
        return cls(name=d["name"], key=str(d["key"]), conditions=conds,
                   margin=float(d.get("margin", 0.1)), enabled=bool(d.get("enabled", True)),
                   hold=max(0.0, float(d.get("hold", 0.0))), delay=max(0.0, float(d.get("delay", 0.0))))


class RuleEngine:
    """State is per pose position, not name: names aren't unique. Reordering poses builds a new engine."""

    def __init__(self, poses: list[Pose]):
        self.poses = poses
        self.active: set[int] = set()
        self.until: dict[int, float] = {}   # pose -> time its hold runs out
        self.since: dict[int, float] = {}   # pose -> time its conditions started holding
        self.state: list[dict] = []

    def update(self, features: dict[str, float], t: float) -> list[dict]:
        self.state = []
        for i, p in enumerate(self.poses):
            conds = [c.holds(features.get(c.feature), i in self.active, p.margin) for c in p.conditions]
            if p.enabled and conds and all(conds):
                self.since.setdefault(i, t)
                if i in self.active or t - self.since[i] >= p.delay:
                    self.until[i] = t + p.hold
            else:
                self.since.pop(i, None)
            now = p.enabled and t <= self.until.get(i, -1.0)
            if now:
                self.active.add(i)
            else:
                self.active.discard(i)
            self.state.append({"active": now, "conds": conds})
        return self.state

    def release(self):
        """Everything off now, holds included: the body is out of frame."""
        self.active.clear()
        self.until.clear()
        self.since.clear()

    def keys(self) -> set[str]:
        return {self.poses[i].key for i in self.active}
