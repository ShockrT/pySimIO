from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

from core.device_registry import DeviceRegistry
from domain.models import ProcessLine, ProcessUnit


@dataclass(slots=True, frozen=True)
class ProcessLineState:
    line_id: str
    name: str
    is_open: bool
    open_elements: tuple[str, ...] = field(default_factory=tuple)
    closed_elements: tuple[str, ...] = field(default_factory=tuple)


class ProcessNetwork:
    """Evaluate process-line state and answer simple directed open-path questions."""

    def __init__(
        self,
        units: Iterable[ProcessUnit] = (),
        lines: Iterable[ProcessLine] = (),
    ) -> None:
        self._units: dict[str, ProcessUnit] = {}
        self._lines: dict[str, ProcessLine] = {}
        self._states: dict[str, ProcessLineState] = {}
        self._outgoing: dict[str, list[str]] = {}
        self._incoming: dict[str, list[str]] = {}
        self.rebuild(units, lines)

    def rebuild(
        self,
        units: Iterable[ProcessUnit],
        lines: Iterable[ProcessLine],
    ) -> None:
        self._units = {unit.id: unit for unit in units}
        self._lines = {line.id: line for line in lines}
        self._states.clear()
        self._outgoing = {unit_id: [] for unit_id in self._units}
        self._incoming = {unit_id: [] for unit_id in self._units}

        for line in self._lines.values():
            self._outgoing.setdefault(line.source_unit_id, []).append(line.id)
            self._incoming.setdefault(line.destination_unit_id, []).append(line.id)

    def evaluate(self, devices: DeviceRegistry) -> dict[str, ProcessLineState]:
        states: dict[str, ProcessLineState] = {}
        for line in self._lines.values():
            opened = tuple(
                element_id
                for element_id in line.control_element_ids
                if devices.is_valve_open(element_id)
            )
            closed = tuple(
                element_id
                for element_id in line.control_element_ids
                if not devices.is_valve_open(element_id)
            )
            states[line.id] = ProcessLineState(
                line_id=line.id,
                name=line.name,
                is_open=line.enabled and not closed,
                open_elements=opened,
                closed_elements=closed,
            )
        self._states = states
        return dict(states)

    def is_line_open(self, line_id: str) -> bool:
        state = self._states.get(line_id)
        return bool(state and state.is_open)

    def has_open_path(
        self,
        source_unit_id: str,
        destination_unit_id: str,
        required_line_id: str | None = None,
    ) -> bool:
        """Return True when an open directed route joins the requested units."""
        if source_unit_id == destination_unit_id:
            return required_line_id is None

        queue: deque[tuple[str, bool]] = deque([(source_unit_id, False)])
        visited: set[tuple[str, bool]] = {(source_unit_id, False)}

        while queue:
            unit_id, required_seen = queue.popleft()
            for line_id in self._outgoing.get(unit_id, ()):
                if not self.is_line_open(line_id):
                    continue
                line = self._lines[line_id]
                next_required_seen = required_seen or line_id == required_line_id
                if line.destination_unit_id == destination_unit_id:
                    if required_line_id is None or next_required_seen:
                        return True
                state = (line.destination_unit_id, next_required_seen)
                if state not in visited:
                    visited.add(state)
                    queue.append(state)
        return False

    def line_has_complete_open_route(self, line_id: str) -> bool:
        """Check whether a line connects at least one open supplier-to-receiver route."""
        line = self._lines.get(line_id)
        if line is None or not self.is_line_open(line_id):
            return False

        supplier_ids = [unit.id for unit in self._units.values() if unit.can_supply]
        receiver_ids = [unit.id for unit in self._units.values() if unit.can_receive]

        return any(
            self.has_open_path(source_id, receiver_id, required_line_id=line_id)
            for source_id in supplier_ids
            for receiver_id in receiver_ids
        )

    def inlet_line_ids(self, unit_id: str) -> tuple[str, ...]:
        return tuple(self._incoming.get(unit_id, ()))

    def outlet_line_ids(self, unit_id: str) -> tuple[str, ...]:
        return tuple(self._outgoing.get(unit_id, ()))

    def states(self) -> dict[str, ProcessLineState]:
        return dict(self._states)
