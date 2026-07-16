from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from core.device_registry import DeviceRegistry
from domain.models import FlowPath


@dataclass(slots=True, frozen=True)
class FlowPathState:
    name: str
    is_open: bool
    open_valves: tuple[str, ...] = field(default_factory=tuple)
    closed_valves: tuple[str, ...] = field(default_factory=tuple)


class FlowPathRuntime:
    """Evaluate each path as open only when every listed valve is open."""

    def __init__(self, paths: Iterable[FlowPath] = ()) -> None:
        self._paths: dict[str, FlowPath] = {}
        self._states: dict[str, FlowPathState] = {}
        self.rebuild(paths)

    def rebuild(self, paths: Iterable[FlowPath]) -> None:
        self._paths = {path.name.casefold(): path for path in paths}
        self._states.clear()

    def evaluate(self, devices: DeviceRegistry) -> dict[str, FlowPathState]:
        states: dict[str, FlowPathState] = {}
        for key, path in self._paths.items():
            opened = tuple(name for name in path.segments if devices.is_valve_open(name))
            closed = tuple(name for name in path.segments if not devices.is_valve_open(name))
            states[key] = FlowPathState(
                name=path.name,
                is_open=bool(path.segments) and not closed,
                open_valves=opened,
                closed_valves=closed,
            )
        self._states = states
        return dict(states)

    def is_open(self, name: str) -> bool:
        if not name:
            return True
        state = self._states.get(name.casefold())
        return bool(state and state.is_open)

    def states(self) -> dict[str, FlowPathState]:
        return {state.name: state for state in self._states.values()}
