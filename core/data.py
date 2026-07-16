from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from domain.models import FlowPath, PlantPaxModule


@dataclass
class Pump:
    name: str
    plc_tag: str
    max_flow: float
    control_variable: str
    fidelity: str = "Simple"


@dataclass
class ControlValve:
    plc_tag: str
    name: str
    cv: float
    open_pct: float = 100.0
    fidelity: str = "Simple"


@dataclass
class ControlVariable:
    plc_tag: str
    name: str = ""
    gain: float = 1.0
    EUMin: float = 0.0
    EUMax: float = 100.0
    value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    serialize_cv = to_dict


@dataclass
class Valve:
    plc_tag: str
    name: str = ""
    tag: str = ""
    is_open: bool = False

    @classmethod
    def from_value(cls, value: str | Mapping[str, Any] | "Valve") -> "Valve":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(plc_tag=value, name=value, tag=value)
        return cls(
            plc_tag=str(value.get("plc_tag") or value.get("tag") or value.get("name") or ""),
            name=str(value.get("name") or value.get("tag") or value.get("plc_tag") or ""),
            tag=str(value.get("tag") or value.get("plc_tag") or ""),
            is_open=bool(value.get("is_open", False)),
        )


@dataclass
class AnalogSensor:
    plc_tag_value: str
    plc_tag_min: str
    plc_tag_max: str
    name: str = ""
    value: float = 0.0
    eu_min: float = 0.0
    eu_max: float = 0.0
    sim_rate: float = 1.0
    model_type: str = ""
    model_configured: bool = False
    active: bool = False
    cv: list[ControlVariable] = field(default_factory=list)
    cv_relationship: list[str] = field(default_factory=list)

    def toggle_active(self) -> None:
        self.active = not self.active

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "cv": [item.to_dict() for item in self.cv],
        }

    serialize_pv = to_dict




class PLCData:
    """In-memory discovery view; persistence is owned by ProjectStore."""

    def __init__(self) -> None:
        self.pax_modules_list: list[PlantPaxModule] = []
        self.pv_list: list[Any] = []
        self.cv_list: list[str] = []
        self.valve_list: list[str] = []
        self.flow_paths: list[FlowPath] = []
        self.module_dict: dict[str, list[PlantPaxModule]] = {}

    def replace_modules(self, modules: Iterable[PlantPaxModule]) -> None:
        self.pax_modules_list = list(modules)
        grouped: dict[str, list[PlantPaxModule]] = {}
        for module in self.pax_modules_list:
            grouped.setdefault(module.module_type, []).append(module)
        self.module_dict = grouped

    def print_tags(self) -> None:
        for pv in self.pv_list:
            print(pv.name)
