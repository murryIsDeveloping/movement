"""Poses as lists of feature conditions. All true -> key held. Hysteresis per condition."""
from dataclasses import dataclass, field, asdict


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

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Pose":
        return cls(
            name=d["name"], key=str(d["key"]),
            conditions=[Condition(c["feature"], c["op"], float(c["value"])) for c in d.get("conditions", [])],
            margin=float(d.get("margin", 0.1)), enabled=bool(d.get("enabled", True)),
        )


class RuleEngine:
    def __init__(self, poses: list[Pose]):
        self.poses = poses
        self.active: set[str] = set()
        self.state: dict[str, dict] = {}

    def update(self, features: dict[str, float]) -> dict[str, dict]:
        for p in self.poses:
            was = p.name in self.active
            conds = [c.holds(features.get(c.feature), was, p.margin) for c in p.conditions]
            now = p.enabled and bool(conds) and all(conds)
            if now:
                self.active.add(p.name)
            else:
                self.active.discard(p.name)
            self.state[p.name] = {"active": now, "conds": conds}
        return self.state

    def keys(self) -> set[str]:
        return {p.key for p in self.poses if p.name in self.active}
