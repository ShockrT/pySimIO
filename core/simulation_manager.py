"""Runtime owner for the pySIMIO simulation lifecycle."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Callable, Iterable

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from domain.models import ConfiguredModel, PlantPaxModule
from persistence.project_store import ProjectStore
from core.plc_sim_bridge import PlcSimBridge
from core.device_registry import DeviceRegistry
from core.flow_path_runtime import FlowPathRuntime
from core.sim_component_factory import SimulationBuild, build_simulation
from core.simulation_validation import SimulationValidator, ValidationReport


logger = logging.getLogger(__name__)


class RuntimeState(str, Enum):
    STOPPED = "Stopped"
    READY = "Ready"
    RUNNING = "Running"
    FAULTED = "Faulted"


class SimulationManager(QObject):
    """Own component building, validation, scheduling, PLC I/O, and runtime state."""

    values_changed = pyqtSignal(dict)
    state_changed = pyqtSignal(object)
    validation_changed = pyqtSignal(object)
    faulted = pyqtSignal(str)

    def __init__(
        self,
        store: ProjectStore,
        plc: Any | None = None,
        *,
        interval_ms: int = 200,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self._plc = plc
        self._interval_ms = max(int(interval_ms), 1)
        self._state = RuntimeState.STOPPED
        self._build = SimulationBuild()
        self._validator = SimulationValidator()
        self._validation = ValidationReport()

        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self.tick)

        self._bridge = PlcSimBridge()
        self._devices = DeviceRegistry(self.store.get_devices())
        self._flow_paths = FlowPathRuntime(self.store.get_flow_paths())
        self._configure_plc_bridge()
        self.build()

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def components(self) -> dict:
        return self._build.components

    @property
    def validation_report(self) -> ValidationReport:
        return self._validation


    @property
    def device_registry(self) -> DeviceRegistry:
        return self._devices

    @property
    def flow_path_states(self) -> dict:
        return self._flow_paths.states()

    @property
    def plc(self) -> Any | None:
        return self._plc

    @property
    def is_plc_connected(self) -> bool:
        checker = getattr(self._plc, "is_connected", None)
        return bool(checker()) if callable(checker) else False

    def set_plc(self, plc: Any | None) -> None:
        was_running = self.state is RuntimeState.RUNNING
        self._bridge.stop()
        self._plc = plc
        self._configure_plc_bridge()
        self._register_outputs()
        if was_running:
            self._bridge.start()

    def build(self, models: Iterable[ConfiguredModel] | None = None) -> ValidationReport:
        """Rebuild runtime objects from persistent configuration."""
        was_running = self.state is RuntimeState.RUNNING
        self._timer.stop()
        self._bridge.stop()

        model_list = list(models) if models is not None else self.store.get_models()
        self._validation = self._validator.validate(model_list)
        self.validation_changed.emit(self._validation)

        try:
            self._build = build_simulation(model_list)
            self._devices.rebuild(self.store.get_devices())
            self._flow_paths.rebuild(self.store.get_flow_paths())
            self._flow_paths.evaluate(self._devices)
            self._register_outputs()
        except Exception as exc:
            logger.exception("Simulation build failed")
            self._build = SimulationBuild()
            self._set_state(RuntimeState.FAULTED)
            self.faulted.emit(str(exc))
            return self._validation

        if self._validation.is_valid:
            self._set_state(RuntimeState.READY)
            if was_running:
                self.start()
        else:
            self._set_state(RuntimeState.FAULTED)

        self.values_changed.emit(self.current_values())
        return self._validation

    def start(self) -> bool:
        """Start simulation scheduling. A PLC connection is not required."""
        if self.state is RuntimeState.RUNNING:
            return True

        if self.state in {RuntimeState.STOPPED, RuntimeState.FAULTED}:
            self.build()

        if not self._validation.is_valid or self._build.orchestrator is None:
            self._set_state(RuntimeState.FAULTED)
            return False

        self._bridge.start()
        self._timer.start()
        self._set_state(RuntimeState.RUNNING)
        return True

    def stop(self) -> None:
        self._timer.stop()
        self._bridge.stop()
        if self._build.orchestrator is not None and self._validation.is_valid:
            self._set_state(RuntimeState.READY)
        else:
            self._set_state(RuntimeState.STOPPED)

    def reset(self) -> ValidationReport:
        self.stop()
        return self.build()

    def tick(self) -> None:
        """Advance one deterministic runtime step."""
        if self.state is not RuntimeState.RUNNING:
            return
        orchestrator = self._build.orchestrator
        if orchestrator is None:
            self._fail("Simulation orchestrator is not available.")
            return

        try:
            self._refresh_device_states()
            self._flow_paths.evaluate(self._devices)
            orchestrator.update(
                self._interval_ms / 1000.0,
                read_value=self._read_external_value,
                is_path_open=self._flow_paths.is_open,
            )
            self._bridge.tick()
            self.values_changed.emit(self.current_values())
        except Exception as exc:
            logger.exception("Simulation tick failed")
            self._fail(str(exc))

    def current_values(self) -> dict[str, float]:
        values: dict[str, float] = {}
        for name, component in self._build.components.items():
            try:
                values[name] = float(component.current_value())
            except Exception:
                logger.exception("Unable to read value for %s", name)
        return values

    def validate(self) -> ValidationReport:
        self._validation = self._validator.validate(self.store.get_models())
        self.validation_changed.emit(self._validation)
        return self._validation

    def synchronize_discovery(self, modules: Iterable[PlantPaxModule]) -> dict[str, list[str]]:
        """Persist discovered modules and rebuild; usable with mocked/offline module lists."""
        result = self.store.sync_discovered_modules(modules)
        self.build()
        return result

    def close(self) -> None:
        self.stop()
        closer = getattr(self._plc, "close", None)
        if callable(closer):
            closer()
        self._plc = None
        self._configure_plc_bridge()


    def _refresh_device_states(self) -> None:
        if not self.is_plc_connected:
            return
        reader = getattr(self._plc, "read_tags", None)
        if not callable(reader):
            return
        tags = self._devices.required_read_tags()
        if tags:
            self._devices.apply_values(reader(tags))

    def _configure_plc_bridge(self) -> None:
        write_fn: Callable[[str, float], bool | None] | None = None
        if self.is_plc_connected:
            candidate = getattr(self._plc, "write_tag", None)
            if callable(candidate):
                write_fn = candidate
        self._bridge.set_write_fn(write_fn)

    def _register_outputs(self) -> None:
        self._bridge.clear_sources()
        models_by_name = {item.name: item for item in self.store.get_models()}
        for name, component in self._build.components.items():
            model = models_by_name.get(name)
            if model and model.active and model.tag:
                self._bridge.register_source(model.tag, component.current_value)

    def _read_external_value(self, name: str) -> float | None:
        if not name or not self.is_plc_connected:
            return None
        reader = getattr(self._plc, "read_tag", None)
        if not callable(reader):
            return None
        value = reader(name)
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    def _fail(self, message: str) -> None:
        self._timer.stop()
        self._bridge.stop()
        self._set_state(RuntimeState.FAULTED)
        self.faulted.emit(message)

    def _set_state(self, state: RuntimeState) -> None:
        if state is self._state:
            return
        self._state = state
        self.state_changed.emit(state)
