from core.device_registry import DeviceRegistry
from core.flow_path_runtime import FlowPathRuntime
from domain.models import DeviceRecord, FlowPath


def _valve(name: str) -> DeviceRecord:
    return DeviceRecord(
        name=name,
        data_type="P_VALVE_DISCRETE",
        category="valve",
        controller_path=name,
        source="manual",
    )


def test_flow_path_opens_only_when_all_valves_are_open() -> None:
    devices = DeviceRegistry([_valve("XV101"), _valve("XV102")])
    paths = FlowPathRuntime([FlowPath(name="Feed", segments=["XV101", "XV102"])])

    devices.set_valve_open("XV101", True)
    paths.evaluate(devices)
    assert not paths.is_open("Feed")
    assert paths.states()["Feed"].open_valves == ("XV101",)
    assert paths.states()["Feed"].closed_valves == ("XV102",)

    devices.set_valve_open("XV102", True)
    paths.evaluate(devices)
    assert paths.is_open("Feed")


def test_registry_builds_and_applies_plantpax_valve_tag() -> None:
    devices = DeviceRegistry([_valve("XV101")])
    assert devices.required_read_tags() == ["XV101.Sts_Open"]
    devices.apply_values({"XV101.Sts_Open": True})
    assert devices.is_valve_open("XV101")
