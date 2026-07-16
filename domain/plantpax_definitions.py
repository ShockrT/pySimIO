from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DeviceCategory(str, Enum):
    PROCESS_VARIABLE = "process_variable"
    CONTROL_VARIABLE = "control_variable"
    VALVE = "valve"
    PUMP = "pump"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class PlantPaxDeviceDefinition:
    data_type: str
    category: DeviceCategory
    read_members: dict[str, str] = field(default_factory=dict)
    write_members: dict[str, str] = field(default_factory=dict)

    def tag(self, base_tag: str, member: str) -> str:
        suffix = self.read_members.get(member) or self.write_members.get(member)
        if suffix is None:
            raise KeyError(f"{self.data_type} has no member named {member!r}")
        return f"{base_tag}{suffix}"


# Central registry for all PlantPAx-specific tag suffixes. Add or correct suffixes
# here as the supported PlantPAx library/version is confirmed.
PLANTPAX_DEVICE_DEFINITIONS: dict[str, PlantPaxDeviceDefinition] = {
    "P_ANALOG_INPUT": PlantPaxDeviceDefinition(
        "P_ANALOG_INPUT",
        DeviceCategory.PROCESS_VARIABLE,
        read_members={"value": ".Val", "eu_min": ".Cfg_PVEUMin", "eu_max": ".Cfg_PVEUMax"},
        write_members={"simulation_value": ".Set_VirtualPV"},
    ),
    "P_ANALOG_OUTPUT": PlantPaxDeviceDefinition(
        "P_ANALOG_OUTPUT",
        DeviceCategory.CONTROL_VARIABLE,
        read_members={"value": ".Val", "eu_min": ".Cfg_CVEUMin", "eu_max": ".Cfg_CVEUMax"},
    ),
    "P_PID": PlantPaxDeviceDefinition(
        "P_PID",
        DeviceCategory.CONTROL_VARIABLE,
        read_members={"value": ".CV", "eu_min": ".Cfg_CVEUMin", "eu_max": ".Cfg_CVEUMax"},
    ),
    "P_VALVE_DISCRETE": PlantPaxDeviceDefinition(
        "P_VALVE_DISCRETE",
        DeviceCategory.VALVE,
        read_members={"is_open": ".Sts_Open"},
    ),
    "P_D4SD": PlantPaxDeviceDefinition(
        "P_D4SD",
        DeviceCategory.VALVE,
        read_members={"is_open": ".Sts_Open"},
    ),
    "P_VARIABLE_SPEED_DRIVE": PlantPaxDeviceDefinition(
        "P_VARIABLE_SPEED_DRIVE",
        DeviceCategory.PUMP,
        read_members={"value": ".Val_SpeedRef"},
    ),
}


def definition_for(data_type: str) -> PlantPaxDeviceDefinition | None:
    return PLANTPAX_DEVICE_DEFINITIONS.get((data_type or "").strip().upper())
