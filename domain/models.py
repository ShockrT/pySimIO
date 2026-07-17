from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(slots=True)
class ConfiguredModel:
    """Persistent configuration for one simulated process variable."""

    name: str
    type: str = "None"
    tag: str = ""
    active: bool = False
    fidelity: int | str = 0
    inputs: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    source: str = "manual"
    discovered_data_type: str = ""
    discovered_path: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ConfiguredModel":
        return cls(
            name=str(data.get("name", "")).strip(),
            type=str(data.get("type", "None")),
            tag=str(data.get("tag", "")),
            active=bool(data.get("active", False)),
            fidelity=data.get("fidelity", 0),
            inputs=dict(data.get("inputs") or {}),
            params=dict(data.get("params") or {}),
            source=str(data.get("source", "manual") or "manual"),
            discovered_data_type=str(data.get("discovered_data_type", "")),
            discovered_path=str(data.get("discovered_path", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DeviceRecord:
    """Persistent PLC/manual device identity used by discovery and runtime state."""

    name: str
    data_type: str
    category: str
    controller_path: str
    source: str = "manual"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DeviceRecord":
        return cls(
            name=str(data.get("name", "")).strip(),
            data_type=str(data.get("data_type", "")).strip(),
            category=str(data.get("category", "other")).strip(),
            controller_path=str(data.get("controller_path") or data.get("path") or data.get("name") or "").strip(),
            source=str(data.get("source", "manual") or "manual"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class FlowPath:
    """Legacy named ordered list of valve/module names used as a process flow path."""

    name: str
    description: str = ""
    segments: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FlowPath":
        return cls(
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")),
            segments=[str(item).strip() for item in (data.get("segments") or []) if str(item).strip()],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProcessUnit:
    """A node in the configured process network."""

    id: str
    name: str
    unit_type: str = "generic"
    description: str = ""
    can_supply: bool = False
    can_receive: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProcessUnit":
        name = str(data.get("name", "")).strip()
        return cls(
            id=str(data.get("id") or name).strip(),
            name=name,
            unit_type=str(data.get("unit_type", "generic") or "generic"),
            description=str(data.get("description", "")),
            can_supply=bool(data.get("can_supply", False)),
            can_receive=bool(data.get("can_receive", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProcessLine:
    """A directed connection between two process units."""

    id: str
    name: str
    source_unit_id: str
    destination_unit_id: str
    control_element_ids: list[str] = field(default_factory=list)
    description: str = ""
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProcessLine":
        name = str(data.get("name", "")).strip()
        return cls(
            id=str(data.get("id") or name).strip(),
            name=name,
            source_unit_id=str(data.get("source_unit_id", "")).strip(),
            destination_unit_id=str(data.get("destination_unit_id", "")).strip(),
            control_element_ids=[
                str(item).strip()
                for item in (data.get("control_element_ids") or [])
                if str(item).strip()
            ],
            description=str(data.get("description", "")),
            enabled=bool(data.get("enabled", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class PlantPaxModule:
    """PLC-discovered PlantPAx module metadata."""

    name: str
    data_type: str
    path: str
    module_type: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PlantPaxModule":
        return cls(
            name=str(data.get("name", "")).strip(),
            data_type=str(data.get("data_type", "")),
            path=str(data.get("path", "")),
            module_type=str(data.get("module_type", "")),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
