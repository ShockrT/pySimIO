"""Offline runtime tests for SimulationManager."""

from pathlib import Path

from PyQt6.QtCore import QCoreApplication

from core.simulation_manager import RuntimeState, SimulationManager
from domain.models import ConfiguredModel, FlowPath, PlantPaxModule
from persistence.project_store import ProjectStore


_app = QCoreApplication.instance() or QCoreApplication([])


def _store(tmp_path: Path, models: list[ConfiguredModel]) -> ProjectStore:
    store = ProjectStore(tmp_path / "project.json")
    store.load()
    store.set_models(models)
    return store


def test_runtime_starts_without_plc(tmp_path: Path) -> None:
    store = _store(
        tmp_path,
        [
            ConfiguredModel(name="CV", type="Sensor", params={"initial": 50}),
            ConfiguredModel(
                name="Flow",
                type="Flow",
                inputs={"control": "CV", "flow_path": "Feed Path"},
                params={
                    "cv_min": 0,
                    "cv_max": 100,
                    "pv_min": 0,
                    "pv_max": 10,
                    "tau": 1,
                    "initial": 0,
                },
            ),
        ],
    )
    store.set_flow_paths([FlowPath(name="Feed Path", segments=["ValveOpen"])])
    store.upsert_model(ConfiguredModel(name="ValveOpen", type="Sensor", params={"initial": 1.0}))
    runtime = SimulationManager(store, plc=None)
    assert runtime.state is RuntimeState.READY
    assert runtime.start()
    runtime.tick()
    assert runtime.current_values()["Flow"] > 0
    runtime.stop()


def test_invalid_runtime_faults_without_starting(tmp_path: Path) -> None:
    store = _store(
        tmp_path,
        [ConfiguredModel(name="Bad", type="Flow", inputs={}, params={})],
    )
    runtime = SimulationManager(store)
    assert runtime.state is RuntimeState.FAULTED
    assert not runtime.start()


def test_discovery_sync_is_testable_without_plc(tmp_path: Path) -> None:
    store = _store(tmp_path, [])
    runtime = SimulationManager(store)
    result = runtime.synchronize_discovery(
        [
            PlantPaxModule(
                name="FIT_101",
                data_type="P_AIn",
                path="Program:Main.FIT_101",
                module_type="AnalogInput",
            )
        ]
    )
    assert result["added"] == ["FIT_101"]
    assert store.get_models()[0].source == "plc_discovery"
