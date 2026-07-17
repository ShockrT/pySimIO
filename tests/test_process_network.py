from core.process_network import ProcessNetwork
from domain.models import ProcessLine, ProcessUnit


class FakeDevices:
    def __init__(self, open_elements: set[str] | None = None) -> None:
        self.open_elements = open_elements or set()

    def is_valve_open(self, name: str) -> bool:
        return name in self.open_elements


def build_network() -> ProcessNetwork:
    units = [
        ProcessUnit(id="source-a", name="Source A", can_supply=True),
        ProcessUnit(id="source-b", name="Source B", can_supply=True),
        ProcessUnit(id="header", name="Header"),
        ProcessUnit(id="tank-a", name="Tank A", can_receive=True),
        ProcessUnit(id="tank-b", name="Tank B", can_receive=True),
    ]
    lines = [
        ProcessLine(
            id="source-a-header",
            name="Source A to Header",
            source_unit_id="source-a",
            destination_unit_id="header",
            control_element_ids=["XV-101"],
        ),
        ProcessLine(
            id="source-b-header",
            name="Source B to Header",
            source_unit_id="source-b",
            destination_unit_id="header",
            control_element_ids=["XV-102"],
        ),
        ProcessLine(
            id="header-tank-a",
            name="Header to Tank A",
            source_unit_id="header",
            destination_unit_id="tank-a",
            control_element_ids=["XV-201"],
        ),
        ProcessLine(
            id="header-tank-b",
            name="Header to Tank B",
            source_unit_id="header",
            destination_unit_id="tank-b",
            control_element_ids=["XV-202"],
        ),
    ]
    return ProcessNetwork(units, lines)


def test_fork_and_merge_paths_are_inferred() -> None:
    network = build_network()
    network.evaluate(FakeDevices({"XV-101", "XV-201", "XV-202"}))

    assert network.has_open_path("source-a", "tank-a")
    assert network.has_open_path("source-a", "tank-b")
    assert not network.has_open_path("source-b", "tank-a")


def test_required_line_must_be_part_of_route() -> None:
    network = build_network()
    network.evaluate(FakeDevices({"XV-101", "XV-201", "XV-202"}))

    assert network.has_open_path(
        "source-a",
        "tank-a",
        required_line_id="header-tank-a",
    )
    assert not network.has_open_path(
        "source-a",
        "tank-a",
        required_line_id="header-tank-b",
    )


def test_line_route_uses_any_available_source_and_sink() -> None:
    network = build_network()
    network.evaluate(FakeDevices({"XV-102", "XV-202"}))

    assert network.line_has_complete_open_route("source-b-header")
    assert network.line_has_complete_open_route("header-tank-b")
    assert not network.line_has_complete_open_route("header-tank-a")


def test_line_without_control_elements_is_open_when_enabled() -> None:
    network = ProcessNetwork(
        [
            ProcessUnit(id="a", name="A", can_supply=True),
            ProcessUnit(id="b", name="B", can_receive=True),
        ],
        [
            ProcessLine(
                id="a-b",
                name="A to B",
                source_unit_id="a",
                destination_unit_id="b",
            )
        ],
    )
    network.evaluate(FakeDevices())

    assert network.is_line_open("a-b")
    assert network.line_has_complete_open_route("a-b")
