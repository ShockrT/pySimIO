from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from domain.models import DeviceRecord
from domain.plantpax_definitions import DeviceCategory, definition_for


@dataclass(slots=True)
class ValveState:
    is_open: bool = False


@dataclass(slots=True)
class AnalogState:
    value: float | None = None
    eu_min: float | None = None
    eu_max: float | None = None


class DeviceRegistry:
    """Runtime view of persisted devices and their latest PLC state."""

    def __init__(self, devices: Iterable[DeviceRecord] = ()) -> None:
        self._devices: dict[str, DeviceRecord] = {}
        self._valves: dict[str, ValveState] = {}
        self._analogs: dict[str, AnalogState] = {}
        self.rebuild(devices)

    def rebuild(self, devices: Iterable[DeviceRecord]) -> None:
        self._devices.clear()
        self._valves.clear()
        self._analogs.clear()
        for device in devices:
            key = device.name.casefold()
            self._devices[key] = device
            if device.category == DeviceCategory.VALVE.value:
                self._valves[key] = ValveState()
            elif device.category in {
                DeviceCategory.PROCESS_VARIABLE.value,
                DeviceCategory.CONTROL_VARIABLE.value,
                DeviceCategory.PUMP.value,
            }:
                self._analogs[key] = AnalogState()

    def required_read_tags(self) -> list[str]:
        tags: list[str] = []
        for device in self._devices.values():
            definition = definition_for(device.data_type)
            if definition is None:
                continue
            tags.extend(definition.tag(device.controller_path, member) for member in definition.read_members)
        return list(dict.fromkeys(tags))

    def apply_values(self, values: dict[str, Any]) -> None:
        for key, device in self._devices.items():
            definition = definition_for(device.data_type)
            if definition is None:
                continue
            if key in self._valves:
                tag = definition.tag(device.controller_path, "is_open")
                self._valves[key].is_open = bool(values.get(tag, False))
                continue
            state = self._analogs.get(key)
            if state is None:
                continue
            for member in ("value", "eu_min", "eu_max"):
                if member not in definition.read_members:
                    continue
                raw = values.get(definition.tag(device.controller_path, member))
                try:
                    setattr(state, member, None if raw is None else float(raw))
                except (TypeError, ValueError):
                    setattr(state, member, None)

    def set_valve_open(self, name: str, is_open: bool) -> None:
        """Offline/test helper for setting a valve state without a PLC."""
        state = self._valves.get(name.casefold())
        if state is not None:
            state.is_open = bool(is_open)

    def is_valve_open(self, name: str) -> bool:
        state = self._valves.get(name.casefold())
        return bool(state and state.is_open)

    def value(self, name: str) -> float | None:
        state = self._analogs.get(name.casefold())
        return None if state is None else state.value
